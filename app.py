from flask import Flask, render_template_string, request, redirect, url_for
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # prevents Tkinter GUI issues
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import io, base64
import os

app = Flask(__name__)

DATA_FILE = "expenses.csv"

# Load data
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
    else:
        df = pd.DataFrame(columns=["ID", "Date", "Category", "Amount"])
        df.to_csv(DATA_FILE, index=False)

    # Ensure correct dtypes
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Ensure ID column exists
    if "ID" not in df.columns:
        df.insert(0, "ID", range(1, len(df) + 1))

    return df


# Save data
def save_data(df):
    df.to_csv(DATA_FILE, index=False)


# Generate charts
def plot_expenses(df):
    img_list = []

    if not df.empty:
        # Category totals
        fig, ax = plt.subplots()
        df.groupby("Category")["Amount"].sum().plot(kind="bar", ax=ax, color="skyblue")
        ax.set_title("Expenses by Category")
        ax.set_ylabel("Amount ($)")
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter('${x:,.2f}'))
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_list.append(base64.b64encode(buf.getvalue()).decode())
        plt.close(fig)

        # Monthly totals
        fig, ax = plt.subplots()
        monthly = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum()
        monthly.index = monthly.index.astype(str)
        monthly.plot(ax=ax, marker="o", color="green")
        ax.set_title("Expenses Over Time")
        ax.set_ylabel("Amount ($)")
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter('${x:,.2f}'))
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_list.append(base64.b64encode(buf.getvalue()).decode())
        plt.close(fig)

    return img_list


# Routes
@app.route("/", methods=["GET", "POST"])
def index():
    df = load_data()

    if request.method == "POST":
        new_row = {
            "ID": df["ID"].max() + 1 if not df.empty else 1,
            "Date": pd.to_datetime(request.form["date"]),
            "Category": request.form["category"],
            "Amount": float(request.form["amount"])
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        return redirect(url_for("index"))

    charts = plot_expenses(df)

    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Expense Tracker Dashboard</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
      <div class="container my-4">
        <h1 class="mb-4 text-center">💰 Expense Tracker Dashboard</h1>

        <!-- Expense Form -->
        <div class="card mb-4 shadow-sm">
          <div class="card-body">
            <h5 class="card-title">Add New Expense</h5>
            <form method="post" class="row g-3">
              <div class="col-md-3">
                <input type="date" class="form-control" name="date" required>
              </div>
              <div class="col-md-3">
                <select class="form-select" name="category" required>
                  <option value="">Choose Category...</option>
                  <option>Food</option>
                  <option>Transport</option>
                  <option>Entertainment</option>
                  <option>Shopping</option>
                  <option>Bills</option>
                  <option>Health</option>
                  <option>Other</option>
                </select>
              </div>
              <div class="col-md-3">
                <input type="number" step="0.01" class="form-control" name="amount" placeholder="Amount" required>
              </div>
              <div class="col-md-3">
                <button type="submit" class="btn btn-primary w-100">Add Expense</button>
              </div>
            </form>
          </div>
        </div>

        <!-- Expenses Table -->
        <div class="card mb-4 shadow-sm">
          <div class="card-body">
            <h5 class="card-title">Expense History</h5>
            <div class="table-responsive">
              <table class="table table-striped table-bordered">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Category</th>
                    <th>Amount</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {% for _, row in df.iterrows() %}
                  <tr>
                    <td>{{ row["Date"].strftime("%Y-%m-%d") if row["Date"] == row["Date"] else "" }}</td>
                    <td>{{ row["Category"] }}</td>
                    <td>${{ "%.2f"|format(row["Amount"]) }}</td>
                    <td>
                      <a href="{{ url_for('delete', row_id=row['ID']) }}" 
                         class="btn btn-sm btn-danger"
                         onclick="return confirm('Delete this expense?');">Delete</a>
                    </td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Charts -->
        <div class="row">
          {% for chart in charts %}
          <div class="col-md-6 mb-4">
            <div class="card shadow-sm">
              <div class="card-body text-center">
                <img src="data:image/png;base64,{{chart}}" class="img-fluid rounded">
              </div>
            </div>
          </div>
          {% endfor %}
        </div>
      </div>
    </body>
    </html>
    """, df=df, charts=charts)


@app.route("/delete/<int:row_id>")
def delete(row_id):
    df = load_data()
    df = df[df["ID"] != row_id]  # filter out the row
    save_data(df)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)