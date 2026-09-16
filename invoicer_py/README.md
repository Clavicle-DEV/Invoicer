# Invoicer — Smart Invoice & Expense Automation (Prototype)

A working Flask prototype for small-business invoicing and expense tracking.

## Stack
- **Flask** (routes/blueprints)
- **Flask-SQLAlchemy** + **SQLite** (data, zero setup)
- **Flask-Login** + Werkzeug password hashing (auth)
- **ReportLab** (PDF invoice generation)
- **Jinja2 + Tailwind (CDN)** (templates, no build step)

## Features implemented
- Register/login/logout (session-based auth, passwords hashed)
- Customers: add, list, search
- Products/services: add, list, search (with default price + tax rate)
- Invoices: create with multiple line items, quick-add from product catalog,
  live subtotal/tax/discount/total calculation in the browser, server-side
  recalculation via model properties (never trusts client math)
- Invoice status: unpaid / paid / overdue, updit anytime
- Expenses: record, filter by category, search by description
- Dashboard: monthly revenue vs. expenses table for a given year, running totals
  (invoiced / paid / unpaid / expenses / net)
- PDF export: click "Download PDF" on any invoice
- Search/filter: customers, products, invoices (by status/number/customer), expenses

## Setup

```bash
cd invoicer_py
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit SECRET_KEY to a random string
```

## Seed demo data (optional but recommended)

```bash
python seed.py
```

This creates a demo login:
- **Email:** demo@example.com
- **Password:** password123

with sample customers, products, a paid and an unpaid invoice, and a few expenses —
useful for seeing the dashboard populated immediately.

## Run

```bash
python run.py
```

Visit **http://localhost:5000**. If you skipped seeding, register a new account
from the login page.

## Project structure

```
invoicer_py/
  run.py                 entry point
  seed.py                 demo data
  app/
    __init__.py           app factory
    extensions.py          db, login_manager
    models.py              User, Customer, Product, Invoice, InvoiceItem, Expense
    auth/routes.py          register/login/logout
    main/routes.py          dashboard, customers, products, invoices, expenses
    utils/pdf.py            ReportLab invoice PDF builder
    utils/reports.py        monthly revenue/expense aggregation
    templates/              Jinja2 + Tailwind (CDN) pages
```

## Design notes worth knowing

- **Money math lives on the model**, not in templates or routes
  (`Invoice.subtotal`, `.tax_total`, `.discount_amount`, `.total` are computed
  properties from the line items) — so it's calculated the same way everywhere:
  screen, PDF, and dashboard.
- **Multi-user by design**: every table has a `user_id` and every query filters
  by `current_user.id`, so this is already safe to have multiple businesses
  using the same instance without seeing each other's data.
- **No JS framework** — the line-item add/remove/live-total on the invoice
  form is ~60 lines of vanilla JS. Fine for a prototype; swap for a proper
  frontend if the UI grows.

## What I'd extend first

1. **Recurring invoices** — add a `RecurringInvoice` template model + a
   scheduled job (APScheduler or a cron calling a Flask CLI command) that
   auto-generates + emails invoices monthly.
2. **Overdue automation** — a daily job that flips `unpaid` invoices past
   `due_date` to `overdue` automatically (right now it's manual).
3. **Email delivery** — send the generated PDF straight to the customer via
   Flask-Mail instead of just download.
4. **Multi-currency** — add a `currency` field and formatting per invoice/customer.
5. **Payments integration** — Stripe/PayPal webhook to auto-mark invoices paid.
6. **Proper migrations** — swap `db.create_all()` for **Flask-Migrate/Alembic**
   before this touches real data, so schema changes don't require dropping tables.
7. **Role-based access** — if a business has multiple staff logins, add a
   `role` field and restrict who can edit vs. just view.
8. **Better reporting** — export the dashboard to CSV/PDF, add per-customer
   and per-product revenue breakdowns, tax-collected reports for filing.
9. **Validation layer** — swap manual `request.form` parsing for
   `Flask-WTF` or `pydantic` schemas as the form count grows.

## A note on testing

I don't have network/internet access in the environment I built this in, so
I couldn't `pip install` and click through the running app myself. Every
`.py` file is syntax-checked (`py_compile`) and the logic was written and
reviewed carefully, but please run it locally and flag anything that breaks —
happy to fix immediately.
