import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def print_section(title: str) -> None:
    """Print a clearly separated section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def run_apple_pricing_analysis(csv_filepath: str) -> pd.DataFrame:
    """Run the complete Apple pricing analysis pipeline."""
    if not os.path.exists(csv_filepath):
        raise FileNotFoundError(f"Dataset not found at: {csv_filepath}")

    df = pd.read_csv(csv_filepath)
    df = df.copy()

    required_columns = [
        "Date",
        "Platform",
        "Product_Category",
        "Model_Name",
        "Condition",
        "Launch_Price_USD",
        "Launch_Price_INR",
        "Current_Price_USD",
        "Current_Price_INR",
        "Discount_Pct",
        "Sale_Event",
        "Stock_Status",
        "Rating",
        "Reviews_Count",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Sale_Event"] = df["Sale_Event"].fillna("Regular Days")
    df["Rating"] = df["Rating"].fillna(df["Rating"].median())
    df["Reviews_Count"] = df["Reviews_Count"].fillna(0).astype(int)

    launch_price_safe = df["Launch_Price_USD"].replace(0, np.nan)
    df["Price_Retention_Percentage"] = np.where(
        launch_price_safe.notna(),
        (df["Current_Price_USD"] / launch_price_safe) * 100,
        np.nan,
    )

    print_section("1. DATASET OVERVIEW")
    print(f"Shape of dataset: {df.shape}")
    print(f"Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    print("\nCore numerical summary:")
    numeric_summary = df[
        [
            "Launch_Price_USD",
            "Current_Price_USD",
            "Discount_Pct",
            "Rating",
            "Reviews_Count",
            "Price_Retention_Percentage",
        ]
    ].describe().T
    print(numeric_summary.round(2).to_string())

    print_section("2. CATEGORY BREAKDOWN")
    category_summary = (
        df.groupby("Product_Category", as_index=False)
        .agg(
            Launch_Price_USD=("Launch_Price_USD", "mean"),
            Current_Price_USD=("Current_Price_USD", "mean"),
            Avg_Discount_Pct=("Discount_Pct", "mean"),
            Avg_Price_Retention_Percentage=("Price_Retention_Percentage", "mean"),
        )
        .sort_values("Avg_Price_Retention_Percentage", ascending=False)
    )
    print(category_summary.round(2).to_string(index=False))

    print_section("3. CONDITION DIFFERENTIAL ANALYSIS")
    condition_filter = df["Condition"].isin(["New", "Renewed/Refurbished"])
    condition_summary = (
        df.loc[condition_filter]
        .groupby("Condition", as_index=False)
        .agg(
            Avg_Current_Price_USD=("Current_Price_USD", "mean"),
            Avg_Discount_Pct=("Discount_Pct", "mean"),
            Avg_Price_Retention_Percentage=("Price_Retention_Percentage", "mean"),
            Avg_Rating=("Rating", "mean"),
            Avg_Reviews=("Reviews_Count", "mean"),
        )
        .sort_values("Condition", ascending=False)
    )
    print(condition_summary.round(2).to_string(index=False))

    print_section("4. PROMOTIONAL EVENT IMPACT")
    promo_summary = (
        df.groupby("Sale_Event", as_index=False)
        .agg(
            Avg_Discount_Pct=("Discount_Pct", "mean"),
            Avg_Reviews=("Reviews_Count", "mean"),
            Observation_Count=("Date", "count"),
        )
        .sort_values("Avg_Discount_Pct", ascending=False)
    )
    print(promo_summary.round(2).to_string(index=False))

    print_section("5. PLATFORM COMPARISON")
    platform_summary = (
        df.groupby("Platform", as_index=False)
        .agg(
            Avg_Current_Price_USD=("Current_Price_USD", "mean"),
            Avg_Discount_Pct=("Discount_Pct", "mean"),
            Avg_Rating=("Rating", "mean"),
            Avg_Reviews=("Reviews_Count", "mean"),
            Out_of_Stock_Rate=("Stock_Status", lambda s: (s == "Out of Stock").mean()),
        )
        .sort_values("Avg_Current_Price_USD", ascending=False)
    )
    print(platform_summary.round(2).to_string(index=False))

    sns.set_theme(style="whitegrid")

    output_dir = Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)

    chart_1_data = (
        df.groupby(["Product_Category", "Condition"], as_index=False)["Price_Retention_Percentage"]
        .mean()
        .sort_values(["Product_Category", "Condition"])
    )
    chart_1_data = chart_1_data[chart_1_data["Condition"].isin(["New", "Renewed/Refurbished"])]

    plt.figure(figsize=(12, 7))
    ax = sns.barplot(
        data=chart_1_data,
        x="Product_Category",
        y="Price_Retention_Percentage",
        hue="Condition",
        palette="viridis",
    )
    ax.set_title("Average Price Retention (%) by Product Category and Condition", fontsize=14, weight="bold")
    ax.set_xlabel("Product Category")
    ax.set_ylabel("Average Price Retention (%)")
    ax.set_ylim(0, 120)

    for container in ax.containers:
        for bar in container.patches:
            height = bar.get_height()
            if np.isnan(height):
                continue
            ax.annotate(
                f"{height:.1f}%",
                (bar.get_x() + bar.get_width() / 2, height),
                ha="center",
                va="bottom",
                fontsize=9,
                rotation=0,
            )

    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(output_dir / "price_retention_by_category_condition.png", dpi=300, bbox_inches="tight")
    plt.close()

    chart_2_data = (
        df.groupby("Sale_Event", as_index=False)["Discount_Pct"]
        .mean()
        .sort_values("Discount_Pct", ascending=False)
    )

    plt.figure(figsize=(10, 6))
    ax = sns.barplot(data=chart_2_data, x="Discount_Pct", y="Sale_Event", palette="magma", orient="h")
    ax.set_title("Impact of Promotional Events on Average Discount (%)", fontsize=14, weight="bold")
    ax.set_xlabel("Average Discount (%)")
    ax.set_ylabel("Promotional Event")
    ax.set_xlim(0, max(chart_2_data["Discount_Pct"].max() * 1.2, 10))

    for bar in ax.patches:
        width = bar.get_width()
        ax.annotate(
            f"{width:.1f}%",
            (width, bar.get_y() + bar.get_height() / 2),
            ha="left",
            va="center",
            fontsize=9,
        )

    plt.tight_layout()
    plt.savefig(output_dir / "promotional_event_discount_impact.png", dpi=300, bbox_inches="tight")
    plt.close()

    print_section("6. VISUALIZATION OUTPUT")
    print(f"Saved chart 1 to: {output_dir / 'price_retention_by_category_condition.png'}")
    print(f"Saved chart 2 to: {output_dir / 'promotional_event_discount_impact.png'}")

    return df


if __name__ == "__main__":
    DATASET_PATH = r"C:\Users\Elijah\Downloads\datasets\Tech Product Pricing Dynamics\apple_products_pricing_2020_2026.csv"
    run_apple_pricing_analysis(DATASET_PATH)
