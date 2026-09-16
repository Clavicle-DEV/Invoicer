from datetime import datetime, date
import random
import string

from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Customer, Product, Invoice, InvoiceItem, Expense
from app.utils.pdf import generate_invoice_pdf
from app.utils.reports import monthly_revenue_and_expenses, summary_totals

main_bp = Blueprint("main", __name__)


def _parse_date(value, default=None):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def _generate_invoice_number():
    stamp = datetime.utcnow().strftime("%Y%m")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"INV-{stamp}-{suffix}"


def _get_or_create_walkin_customer():
    """Fallback customer for quick sales when no specific customer is picked."""
    walkin = Customer.query.filter_by(user_id=current_user.id, name="Walk-in Customer").first()
    if not walkin:
        walkin = Customer(user_id=current_user.id, name="Walk-in Customer")
        db.session.add(walkin)
        db.session.commit()
    return walkin


# ---------- Dashboard ----------

@main_bp.route("/")
@login_required
def dashboard():
    year = request.args.get("year", type=int) or date.today().year
    months = monthly_revenue_and_expenses(current_user.id, year)
    totals = summary_totals(current_user.id)
    recent_invoices = (
        Invoice.query.filter_by(user_id=current_user.id)
        .order_by(Invoice.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "dashboard.html",
        months=months,
        totals=totals,
        year=year,
        recent_invoices=recent_invoices,
    )


# ---------- Customers ----------

@main_bp.route("/customers")
@login_required
def customers():
    q = request.args.get("q", "").strip()
    query = Customer.query.filter_by(user_id=current_user.id)
    if q:
        query = query.filter(Customer.name.ilike(f"%{q}%"))
    all_customers = query.order_by(Customer.name).all()
    return render_template("customers.html", customers=all_customers, q=q)


@main_bp.route("/customers/new", methods=["GET", "POST"])
@login_required
def new_customer():
    if request.method == "POST":
        customer = Customer(
            user_id=current_user.id,
            name=request.form.get("name", "").strip(),
            email=request.form.get("email", "").strip(),
            phone=request.form.get("phone", "").strip(),
            address=request.form.get("address", "").strip(),
        )
        if not customer.name:
            flash("Customer name is required.", "error")
            return render_template("customer_form.html")
        db.session.add(customer)
        db.session.commit()
        flash("Customer added.", "success")
        return redirect(url_for("main.customers"))
    return render_template("customer_form.html")


# ---------- Products ----------

@main_bp.route("/products")
@login_required
def products():
    q = request.args.get("q", "").strip()
    query = Product.query.filter_by(user_id=current_user.id)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    all_products = query.order_by(Product.name).all()
    return render_template("products.html", products=all_products, q=q)


@main_bp.route("/products/new", methods=["GET", "POST"])
@login_required
def new_product():
    if request.method == "POST":
        try:
            unit_price = float(request.form.get("unit_price", 0) or 0)
            tax_rate = float(request.form.get("tax_rate", 0) or 0)
        except ValueError:
            flash("Price and tax rate must be numbers.", "error")
            return render_template("product_form.html")

        product = Product(
            user_id=current_user.id,
            name=request.form.get("name", "").strip(),
            description=request.form.get("description", "").strip(),
            unit_price=unit_price,
            tax_rate=tax_rate,
        )
        if not product.name:
            flash("Product name is required.", "error")
            return render_template("product_form.html")
        db.session.add(product)
        db.session.commit()
        flash("Product added.", "success")
        return redirect(url_for("main.products"))
    return render_template("product_form.html")


# ---------- Invoices ----------

@main_bp.route("/invoices")
@login_required
def invoices():
    status = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()

    query = Invoice.query.filter_by(user_id=current_user.id)
    if status:
        query = query.filter(Invoice.status == status)
    if q:
        query = query.join(Customer).filter(
            db.or_(
                Invoice.invoice_number.ilike(f"%{q}%"),
                Customer.name.ilike(f"%{q}%"),
            )
        )
    all_invoices = query.order_by(Invoice.created_at.desc()).all()
    return render_template("invoices.html", invoices=all_invoices, status=status, q=q)


@main_bp.route("/invoices/new", methods=["GET", "POST"])
@login_required
def new_invoice():
    customers_list = Customer.query.filter_by(user_id=current_user.id).order_by(Customer.name).all()
    products_list = Product.query.filter_by(user_id=current_user.id).order_by(Product.name).all()

    if not customers_list:
        flash("Add a customer before creating an invoice.", "error")
        return redirect(url_for("main.new_customer"))

    if request.method == "POST":
        customer_id = request.form.get("customer_id", type=int)
        discount_percent = float(request.form.get("discount_percent", 0) or 0)
        due_date = _parse_date(request.form.get("due_date"))
        notes = request.form.get("notes", "").strip()

        descriptions = request.form.getlist("item_description")
        quantities = request.form.getlist("item_quantity")
        unit_prices = request.form.getlist("item_unit_price")
        tax_rates = request.form.getlist("item_tax_rate")

        if not customer_id or not descriptions:
            flash("Select a customer and add at least one line item.", "error")
            return render_template(
                "invoice_form.html", customers=customers_list, products=products_list
            )

        invoice = Invoice(
            user_id=current_user.id,
            customer_id=customer_id,
            invoice_number=_generate_invoice_number(),
            issue_date=date.today(),
            due_date=due_date,
            discount_percent=discount_percent,
            notes=notes,
            status="unpaid",
        )
        db.session.add(invoice)

        for desc, qty, price, tax in zip(descriptions, quantities, unit_prices, tax_rates):
            if not desc.strip():
                continue
            item = InvoiceItem(
                invoice=invoice,
                description=desc.strip(),
                quantity=float(qty or 0),
                unit_price=float(price or 0),
                tax_rate=float(tax or 0),
            )
            db.session.add(item)

        db.session.commit()
        flash(f"Invoice {invoice.invoice_number} created.", "success")
        return redirect(url_for("main.invoice_detail", invoice_id=invoice.id))

    return render_template("invoice_form.html", customers=customers_list, products=products_list)


@main_bp.route("/invoices/<int:invoice_id>")
@login_required
def invoice_detail(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    return render_template("invoice_detail.html", invoice=invoice)


@main_bp.route("/invoices/<int:invoice_id>/status", methods=["POST"])
@login_required
def update_invoice_status(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    new_status = request.form.get("status")
    if new_status in ("paid", "unpaid", "overdue"):
        invoice.status = new_status
        db.session.commit()
        flash(f"Invoice marked as {new_status}.", "success")
    return redirect(url_for("main.invoice_detail", invoice_id=invoice.id))


@main_bp.route("/invoices/<int:invoice_id>/pdf")
@login_required
def invoice_pdf(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    pdf_bytes = generate_invoice_pdf(invoice, current_user, invoice.customer)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number}.pdf"
        },
    )


# ---------- Quick Sale (fast counter checkout) ----------

@main_bp.route("/quick-sale")
@login_required
def quick_sale():
    products_list = Product.query.filter_by(user_id=current_user.id).order_by(Product.name).all()
    customers_list = Customer.query.filter_by(user_id=current_user.id).order_by(Customer.name).all()
    if not products_list:
        flash("Add at least one product first so you can tap it in during checkout.", "error")
        return redirect(url_for("main.new_product"))
    return render_template("quick_sale.html", products=products_list, customers=customers_list)


@main_bp.route("/api/quick-sale", methods=["POST"])
@login_required
def quick_sale_checkout():
    data = request.get_json(silent=True) or {}
    cart = data.get("items", [])
    customer_id = data.get("customer_id")

    if not cart:
        return jsonify({"error": "Cart is empty."}), 400

    if customer_id:
        customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first()
        if not customer:
            return jsonify({"error": "Customer not found."}), 400
    else:
        customer = _get_or_create_walkin_customer()

    invoice = Invoice(
        user_id=current_user.id,
        customer_id=customer.id,
        invoice_number=_generate_invoice_number(),
        issue_date=date.today(),
        status="paid",  # counter sales are settled on the spot
        discount_percent=0,
    )
    db.session.add(invoice)
    db.session.flush()  # get invoice.id before adding items

    for entry in cart:
        product = Product.query.filter_by(id=entry.get("product_id"), user_id=current_user.id).first()
        if not product:
            continue
        qty = float(entry.get("quantity") or 1)
        if qty <= 0:
            continue
        db.session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                description=product.name,
                quantity=qty,
                unit_price=product.unit_price,
                tax_rate=product.tax_rate,
            )
        )

    db.session.commit()

    if not invoice.items:
        db.session.delete(invoice)
        db.session.commit()
        return jsonify({"error": "None of the cart items were valid."}), 400

    return jsonify(
        {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "total": invoice.total,
            "customer_name": customer.name,
            "pdf_url": url_for("main.invoice_pdf", invoice_id=invoice.id),
            "detail_url": url_for("main.invoice_detail", invoice_id=invoice.id),
        }
    )


# ---------- Expenses ----------

@main_bp.route("/expenses")
@login_required
def expenses():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    query = Expense.query.filter_by(user_id=current_user.id)
    if category:
        query = query.filter(Expense.category == category)
    if q:
        query = query.filter(Expense.description.ilike(f"%{q}%"))
    all_expenses = query.order_by(Expense.date.desc()).all()

    categories = [
        c[0]
        for c in db.session.query(Expense.category)
        .filter_by(user_id=current_user.id)
        .distinct()
        .all()
    ]
    return render_template(
        "expenses.html", expenses=all_expenses, q=q, category=category, categories=categories
    )


@main_bp.route("/expenses/new", methods=["GET", "POST"])
@login_required
def new_expense():
    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0) or 0)
        except ValueError:
            flash("Amount must be a number.", "error")
            return render_template("expense_form.html")

        expense = Expense(
            user_id=current_user.id,
            category=request.form.get("category", "").strip() or "Uncategorized",
            description=request.form.get("description", "").strip(),
            amount=amount,
            date=_parse_date(request.form.get("date"), default=date.today()),
        )
        db.session.add(expense)
        db.session.commit()
        flash("Expense recorded.", "success")
        return redirect(url_for("main.expenses"))
    return render_template("expense_form.html")
