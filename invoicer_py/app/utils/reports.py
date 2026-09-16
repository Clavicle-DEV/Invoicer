from collections import OrderedDict
from datetime import date
from sqlalchemy import extract
from app.extensions import db
from app.models import Invoice, InvoiceItem, Expense


def monthly_revenue_and_expenses(user_id, year=None):
    """Returns an OrderedDict {month_number: {'revenue': x, 'expenses': y}} for the given year."""
    year = year or date.today().year
    months = OrderedDict((m, {"revenue": 0.0, "expenses": 0.0}) for m in range(1, 13))

    paid_invoices = (
        Invoice.query.filter_by(user_id=user_id, status="paid")
        .filter(extract("year", Invoice.issue_date) == year)
        .all()
    )
    for inv in paid_invoices:
        m = inv.issue_date.month
        months[m]["revenue"] += inv.total

    expenses = (
        Expense.query.filter_by(user_id=user_id)
        .filter(extract("year", Expense.date) == year)
        .all()
    )
    for exp in expenses:
        m = exp.date.month
        months[m]["expenses"] += exp.amount

    for m in months:
        months[m]["revenue"] = round(months[m]["revenue"], 2)
        months[m]["expenses"] = round(months[m]["expenses"], 2)
        months[m]["net"] = round(months[m]["revenue"] - months[m]["expenses"], 2)

    return months


def summary_totals(user_id):
    invoices = Invoice.query.filter_by(user_id=user_id).all()
    total_invoiced = round(sum(i.total for i in invoices), 2)
    total_paid = round(sum(i.total for i in invoices if i.status == "paid"), 2)
    total_unpaid = round(sum(i.total for i in invoices if i.status != "paid"), 2)
    total_expenses = round(
        sum(e.amount for e in Expense.query.filter_by(user_id=user_id).all()), 2
    )
    return {
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "total_unpaid": total_unpaid,
        "total_expenses": total_expenses,
        "net": round(total_paid - total_expenses, 2),
    }
