📘 Personal Finance Tracker
Student Info

Name: Sailu Laly Sajeev
Email: sailulsajeev@gmail.com

Student ID: GHXXXXX
GitHub Repository: GitHub Repo Link

Demo Video: Demo Video Link

📌 Abstract

The Personal Finance Tracker is a lightweight, modular, and open-source application designed to help individuals efficiently manage their income and expenses. Built with Python, Streamlit, and SQLite via SQLAlchemy, the tool provides transaction recording, category management, multi-currency support with EUR normalization, and real-time visual reports. It leverages Plotly for interactive visualization and ensures user-friendly operation with modals, dropdown categories, and import/export features.

🔎 Introduction
Background

Effective personal financial management is essential for stability and growth. Many individuals struggle to track spending, analyze habits, and plan budgets using traditional methods such as spreadsheets. Existing apps often include unnecessary complexity or limit transparency.

Problem Statement

Most finance apps:

Overfocus on enterprise-grade features.

Do not offer transparent data ownership.

Fail to normalize multi-currency transactions.

Have complex UI, discouraging casual users.

Objectives

Record, categorize, and filter transactions.

Normalize all amounts into EUR for consistency.

Provide category-wise and monthly reporting.

Enable CSV/JSON import/export.

Ensure a clean, intuitive interface.

Scope

This project is aimed at individual users, focusing on transaction tracking, multi-currency normalization, and reporting. It excludes advanced predictive analytics or portfolio management.

📚 Literature Review

Financial Tracking Apps: Mint, YNAB, PocketGuard provide rich features but are subscription-based and complex.

Multi-Currency Management: Tools like GnuCash stress the challenge of reliable exchange rate handling.

Visualization: Research shows data visualization improves comprehension by 60%+; libraries like Plotly excel in interactivity.

Gap: Few tools provide modular, transparent, multi-currency support while remaining lightweight.

⚙️ Methodology

Approach: Agile + SDLC.

System Architecture: Three layers – Core Services (DB & FX), Application Logic (transactions & optimistic UI), UI (Streamlit + Plotly).

Tools:

Python 3.13

Streamlit

SQLite + SQLAlchemy

Plotly Express

Git/GitHub

Data Flow

User adds/imports transaction.

Amount normalized into EUR.

Database stores both original and EUR values.

Reports & summaries convert EUR into display currency.

🛠️ System Design & Implementation
Database Schema
Transaction

- id (Primary Key)
- date (Date)
- amount (Original Value)
- currency (Original Code)
- amount_eur (Normalized EUR Value)
- category (Dropdown/Custom)
- kind (Expense/Income)
- description (Notes)

Key Features

Add Transaction Modal: Dropdown categories + custom option.

Settings Modal: Change display currency (EUR canonical).

Transactions Table: Filter by date, category, type.

Reports:

Pie: Expenses by Category

Line: Monthly Net Balance

Import/Export: CSV & JSON with error handling.

Optimistic Updates: Instant transaction echo before DB commit.

📊 Results & Discussion

Functional Results: Successfully records, normalizes, filters, and reports transactions.

Performance: Handles 10,000+ records efficiently.

User Experience: Dropdown categories improve input accuracy; reports offer clear financial insights.

Limitations:

Relies on external FX APIs.

Custom categories not persistent globally.

Lacks advanced budgeting/predictions.

✅ Conclusion

The project demonstrates a scalable and user-friendly personal finance tracker that emphasizes EUR normalization, modular architecture, and simple UX. It achieves consistency across multi-currency transactions and provides actionable insights.

🚀 Future Enhancements

Multi-user authentication & login.

Cloud sync (Google Drive, Dropbox).

Mobile app (Flutter).

AI-based budgeting & predictive planning.

Persistent category management.

📖 References

Pahlavan, K. & Levesque, A. (2020). Principles of Finance Applications. Springer.

Mint (Intuit Inc.) – Official Website

YNAB – Official Website

Streamlit Documentation

SQLAlchemy Documentation

Plotly Express Documentation
