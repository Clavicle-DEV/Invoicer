"""
Seeds the database with a demo user, customers, products, invoices, and expenses.
Run with: python seed.py
"""
from datetime import date, timedelta
from app import create_app
from app.extensions import db
from app.models import User, Customer, Product, Invoice, InvoiceItem, Expense

app = create_app()

with app.app_context():
    if User.query.filter_by(email="demo@example.com").first():
        print("Demo data already exists. Skipping.")
    else:
        user = User(name="Demo Owner", email="demo@example.com", business_name="Demo Trading Co.")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        c1 = Customer(user_id=user.id, name="Acme Retailers", email="acme@example.com", phone="555-0101", address="12 Market St")
        c2 = Customer(user_id=user.id, name="Northgate Supplies", email="northgate@example.com", phone="555-0102", address="88 Industrial Ave")
        db.session.add_all([c1, c2])
        db.session.commit()

        p1 = Product(user_id=user.id, name="Consulting (hourly)", description="General business consulting", unit_price=50.0, tax_rate=16)
        p2 = Product(user_id=user.id, name="Web Design Package", description="5-page website", unit_price=800.0, tax_rate=16)
        db.session.add_all([p1, p2])
        db.session.commit()

        inv1 = Invoice(
            user_id=user.id, customer_id=c1.id, invoice_number="INV-DEMO-0001",
            issue_date=date.today() - timedelta(days=20), due_date=date.today() + timedelta(days=10),
            status="paid", discount_percent=5,
        )
        db.session.add(inv1)
        db.session.commit()
        db.session.add_all([
            InvoiceItem(invoice_id=inv1.id, description="Consulting - March", quantity=10, unit_price=50.0, tax_rate=16),
            InvoiceItem(invoice_id=inv1.id, description="Web Design Package", quantity=1, unit_price=800.0, tax_rate=16),
        ])

        inv2 = Invoice(
            user_id=user.id, customer_id=c2.id, invoice_number="INV-DEMO-0002",
            issue_date=date.today() - timedelta(days=5), due_date=date.today() + timedelta(days=25),
            status="unpaid", discount_percent=0,
        )
        db.session.add(inv2)
        db.session.commit()
        db.session.add(InvoiceItem(invoice_id=inv2.id, description="Consulting - April", quantity=6, unit_price=50.0, tax_rate=16))

        db.session.add_all([
            Expense(user_id=user.id, category="Rent", description="Office rent", amount=300, date=date.today() - timedelta(days=15)),
            Expense(user_id=user.id, category="Supplies", description="Printer paper & ink", amount=45.50, date=date.today() - timedelta(days=8)),
            Expense(user_id=user.id, category="Utilities", description="Internet bill", amount=60, date=date.today() - timedelta(days=3)),
        ])

        db.session.commit()
        print("Seeded demo data.")
        print("Login with: demo@example.com / password123")
