import numpy as np

# Helper function to calculate remaining debt after a certain number of months
def calculate_remaining_debt(initial_principal, monthly_rate, fixed_monthly_payment, num_payments_to_simulate, loan_payment_term_months):
    """
    Calculates the remaining loan balance after a specific number of months
    by simulating month-by-month payments and interest accrual.

    Args:
        initial_principal: The starting loan amount.
        monthly_rate: The monthly interest rate (as a decimal).
        fixed_monthly_payment: The constant monthly payment amount.
        num_payments_to_simulate: The number of months to simulate forward.
        loan_payment_term_months: The total number of months the loan payments are scheduled for.

    Returns:
        The remaining loan balance after num_payments_to_simulate months.
    """
    current_balance = initial_principal
    # If the loan starts at 0 or less, it's already paid off.
    if current_balance <= 0:
        return 0

    for month_index in range(num_payments_to_simulate):
        # If balance is non-positive, loan is paid off, stop simulation.
        if current_balance <= 0:
            break

        # Calculate interest for the current month based on the balance at the start of the month.
        interest_for_month = current_balance * monthly_rate

        # Determine the payment amount for this month.
        payment_made_this_month = 0
        # Payments are only made if the current month is within the loan's payment term.
        if month_index < loan_payment_term_months:
            payment_made_this_month = fixed_monthly_payment

        # Add accrued interest to the balance.
        current_balance += interest_for_month

        # Check if the payment covers the entire remaining balance (including interest).
        if payment_made_this_month >= current_balance:
            current_balance = 0 # Loan is paid off.
        else:
            # Subtract the payment from the balance.
            current_balance -= payment_made_this_month

        # Ensure the balance doesn't dip below zero due to floating-point inaccuracies.
        if current_balance < 0:
            current_balance = 0

    return current_balance

# Helper function to get a value that increments yearly at a specific year
def get_yearly_incrementing_value(initial_val, rate, target_year):
    """
    Calculates the value of an item that increases by a fixed rate annually,
    determining its value during a specific target year.

    Args:
        initial_val: The starting value at year 0.
        rate: The annual growth rate (as a decimal).
        target_year: The year for which to calculate the value (0-indexed).

    Returns:
        The value during the specified target_year.
    """
    # The value increments at the start of each year (after year 0).
    # Value during year 0 (months 0-11) is initial_val * (1+rate)^0
    # Value during year 1 (months 12-23) is initial_val * (1+rate)^1
    # Value during year N (months 12N to 12(N+1)-1) is initial_val * (1+rate)^N
    if target_year < 0:
        # Handle invalid input, perhaps return initial_val or raise error
        return initial_val # Or raise ValueError("target_year cannot be negative")
    return initial_val * (1 + rate) ** target_year


def get_data_at_year(
    target_year, # The specific year (integer, 0-indexed) to calculate values for
    initial_rent=1500,
    home_price=800000,
    down_payment_perc=0.20,
    loan_term_years=30,
    loan_interest=0.065,
    property_tax_rate=0.0105,
    stock_interest=0.11,
    home_value_interest=0.054,
    home_upkeep_percent=0.01,
    tenant_rent_initial=0 # Renamed from tenant_rent for clarity
    ):
    """
    Calculates key financial metrics for renting vs. buying at a specific target year,
    without generating the full time series history. This version is faster for single-point calculations.

    Args:
        target_year: The year number (e.g., 10 for the end of year 10) for calculation.
                     Year 0 represents the initial state.
        initial_rent: Starting monthly rent.
        home_price: Initial purchase price of the home.
        down_payment_perc: Down payment percentage (e.g., 0.20 for 20%).
        loan_term_years: The term of the mortgage in years.
        loan_interest: Annual loan interest rate (e.g., 0.065 for 6.5%).
        property_tax_rate: Annual property tax rate as a percentage of home value.
        stock_interest: Expected annual growth rate of stock investments.
        home_value_interest: Expected annual appreciation rate of the home value.
        home_upkeep_percent: Annual home upkeep cost as a percentage of home value.
        tenant_rent_initial: Initial monthly rent received from tenants (if any).

    Returns:
        A dictionary containing the calculated financial metrics for the state *after*
        target_year has completed (i.e., at the end of month target_year * 12).
        Returns None if target_year is negative.
    """

    if target_year < 0:
        # Or raise ValueError("target_year must be non-negative.")
        print("Error: target_year must be non-negative.")
        return None

    # --- Basic Calculations ---
    # Calculate values at the end of target_year, which means simulating target_year * 12 months.
    num_months_to_simulate = target_year * 12
    yearly_payments = 12

    # Convert annual rates to monthly rates for calculations
    # Handle potential division by zero or invalid operations if rates are -1 (-100%)
    monthly_loan_interest_rate = (1 + loan_interest)**(1/12) - 1 if loan_interest > -1 else 0
    monthly_stock_interest = (1 + stock_interest)**(1/12) - 1 if stock_interest > -1 else 0
    # We use the annual home value interest directly with the yearly helper function

    # Calculate initial loan details
    loan_principal = home_price * (1 - down_payment_perc)
    down_payment = home_price - loan_principal
    loan_payment_term_months = loan_term_years * yearly_payments

    # Calculate fixed monthly mortgage payment (P&I)
    monthly_payment = 0
    if loan_principal > 0 and loan_payment_term_months > 0:
        if monthly_loan_interest_rate > 1e-9: # Use threshold for floating point comparison
             # Standard amortization formula
             rate = monthly_loan_interest_rate
             n = loan_payment_term_months
             monthly_payment = loan_principal * (rate * (1 + rate) ** n) / ((1 + rate) ** n - 1)
        else: # Handle 0% interest rate case (or very close to 0)
             monthly_payment = loan_principal / loan_payment_term_months


    # --- Calculate Point-in-Time Homeowner Values at end of target_year ---

    # Home value appreciates annually. Value *during* target_year is based on target_year increments.
    home_value_at_target = get_yearly_incrementing_value(home_price, home_value_interest, target_year)

    # Calculate remaining debt *after* num_months_to_simulate have passed.
    remaining_debt_at_target = calculate_remaining_debt(
        loan_principal,
        monthly_loan_interest_rate,
        monthly_payment,
        num_months_to_simulate, # Calculate debt after this many months
        loan_payment_term_months
    )

    # Net worth is the appreciated home value minus the remaining debt.
    net_worth_with_home_at_target = home_value_at_target - remaining_debt_at_target

    # --- Calculate Point-in-Time Renter Values at end of target_year ---

    # Simulate month-by-month investment growth for the renter scenario up to the target month.
    # This is necessary because the amount invested changes yearly.
    cumulative_investment_renting = 0

    # Loop through each month from the start up to the end of the target year.
    for month_index in range(num_months_to_simulate):
        # Determine the current year (0-indexed) based on the month index.
        current_year = month_index // 12

        # Get values that change annually, based on the current year of the simulation.
        current_rent_value = get_yearly_incrementing_value(initial_rent, home_value_interest, current_year)
        current_home_value_for_costs = get_yearly_incrementing_value(home_price, home_value_interest, current_year)
        current_tenant_rent = get_yearly_incrementing_value(tenant_rent_initial, home_value_interest, current_year)

        # Calculate homeowner's costs for *this specific month* to find the comparison point.
        prop_tax_monthly = current_home_value_for_costs * property_tax_rate / 12
        upkeep_monthly = current_home_value_for_costs * home_upkeep_percent / 12
        # Determine if a mortgage payment is made in this month.
        mortgage_payment_this_month = monthly_payment if month_index < loan_payment_term_months else 0

        # Total cash outflow for the homeowner this month (excluding down payment initially).
        paid_towards_home_this_month = (
            mortgage_payment_this_month
            + prop_tax_monthly
            + upkeep_monthly
            - current_tenant_rent # Subtract tenant rent income
        )
        # Add the one-time down payment cost in the very first month (month 0).
        if month_index == 0:
            paid_towards_home_this_month += down_payment

        # Renter's cost this month is simply the rent.
        rent_this_month = current_rent_value

        # Calculate the difference in cash flow: money the renter *didn't* spend compared to the homeowner.
        # This is the amount assumed to be invested by the renter each month.
        excess_available = paid_towards_home_this_month - rent_this_month

        # Update the renter's cumulative investment:
        # 1. Grow the existing investment by one month's stock interest.
        # 2. Add the excess cash available from this month.
        cumulative_investment_renting = cumulative_investment_renting * (1 + monthly_stock_interest) + excess_available

    # The final value after the loop is the renter's total investment value at the end of the target year.
    net_worth_renting_at_target = cumulative_investment_renting

    # --- Final Calculations (Taxes, Fees) ---
    # These represent potential costs/reductions if assets were liquidated at the target time.
    CAPITAL_GAINS_TAX_RATE = 0.15 # Assumed tax rate on investment gains
    REALTOR_COST = 0.06 # Assumed cost to sell the home as a percentage of home value

    # Calculate potential capital gains tax on the renter's investments.
    # Note: This is a simplification; actual tax depends on cost basis and holding period.
    capital_gains_tax = net_worth_renting_at_target * CAPITAL_GAINS_TAX_RATE
    effective_net_worth_renting = net_worth_renting_at_target - capital_gains_tax

    # Calculate potential realtor fees if the home were sold at the target time.
    realtor_fees_if_selling = home_value_at_target * REALTOR_COST
    # Effective net worth after potential selling costs.
    effective_net_worth_with_home = net_worth_with_home_at_target - realtor_fees_if_selling

    # --- Return Results ---
    # Compile the calculated metrics into a dictionary.
    results = {
        "target_year": target_year,
        "months_simulated": num_months_to_simulate,
        "home_value": home_value_at_target,
        "remaining_debt": remaining_debt_at_target,
        "home_equity": home_value_at_target - remaining_debt_at_target, # Added for clarity
        "net_worth_with_home": net_worth_with_home_at_target,
        "net_worth_renting": net_worth_renting_at_target,
        "effective_net_worth_with_home": effective_net_worth_with_home, # After realtor fees
        "effective_net_worth_renting": effective_net_worth_renting,       # After potential capital gains
        # Add other potentially useful point-in-time values if needed for comparison
        "monthly_mortgage_payment_during_year": monthly_payment if num_months_to_simulate < loan_payment_term_months else 0,
        "monthly_property_tax_during_year": get_yearly_incrementing_value(home_price, home_value_interest, target_year) * property_tax_rate / 12,
        "monthly_home_upkeep_during_year": get_yearly_incrementing_value(home_price, home_value_interest, target_year) * home_upkeep_percent / 12,
        "monthly_rent_during_year": get_yearly_incrementing_value(initial_rent, home_value_interest, target_year),
        "monthly_tenant_rent_during_year": get_yearly_incrementing_value(tenant_rent_initial, home_value_interest, target_year)
    }

    return results

# --- Example Usage ---
# Calculate metrics for the end of year 10
# year_10_data = get_data_at_year(target_year=10) # Use default parameters
# if year_10_data:
#     print("--- Data at End of Year 10 ---")
#     for key, value in year_10_data.items():
#         print(f"{key}: {value:,.2f}")

# # Calculate metrics for the end of year 30
# year_30_data = get_data_at_year(
#     target_year=30,
#     initial_rent=2000,
#     home_price=1000000,
#     loan_interest=0.07,
#     stock_interest=0.10,
#     home_value_interest=0.06
# )
# if year_30_data:
#     print("\n--- Data at End of Year 30 (Custom Params) ---")
#     for key, value in year_30_data.items():
#         print(f"{key}: {value:,.2f}")

def get_buying_diff(at_year,
                    initial_rent,
                    home_price,
                    down_payment_perc,
                    loan_term_years,
                    loan_interest,
                    property_tax_rate,
                    stock_interest,
                    home_value_interest,
                    tenant_rent_initial,
                    ):
    result = get_data_at_year(
        target_year=at_year,
             initial_rent=initial_rent,
             home_price=home_price,
             down_payment_perc=down_payment_perc,
             loan_term_years=loan_term_years,
             loan_interest=loan_interest,
             property_tax_rate=property_tax_rate,
             stock_interest=stock_interest,
             home_value_interest=home_value_interest,
             tenant_rent_initial=tenant_rent_initial)
    return result['effective_net_worth_with_home'] - result['effective_net_worth_renting']

import numpy as np

def grid_search_buying_diff(param_ranges=None, **kwargs):
    """
    Performs a grid search over specified parameters to find the buying diff 
    at a specific year.

    Args:
      at_year: The year at which to calculate the buying diff.
      initial_rent: Initial rent amount.
      home_price: Home price.
      down_payment_perc: Down payment percentage.
      loan_term_years: Loan term in years.
      loan_interest: Loan interest rate.
      property_tax_rate: Property tax rate.
      stock_interest: Stock investment interest rate.
      home_value_interest: Home value appreciation interest rate.
      param_ranges: A dictionary where keys are parameter names and values 
                    are tuples (start, stop, step) for the range.

    Returns:
      A dictionary containing:
        - 'results': A NumPy array with the buying diff values.
        - 'param_values': A dictionary with parameter names as keys and lists of 
                          parameter values used in the grid search as values.
    """


    if param_ranges is None:
        param_ranges = {}

    # Validation
    valid_params = [
        "at_year",
        "initial_rent",
        "home_price",
        "down_payment_perc",
        "loan_term_years",
        "loan_interest",
        "property_tax_rate",
        "stock_interest",
        "home_value_interest",
        "tenant_rent_initial"
    ]

    for param in valid_params:
        if param in param_ranges and param in kwargs:
            raise ValueError(
                f"Parameter '{param}' cannot be specified as both a constant and a range."
            )
        if param not in param_ranges and param not in kwargs:
            raise ValueError(f"Parameter '{param}' must be specified.")

    param_values = {}
    for param_name, (start, stop, step) in param_ranges.items():
        param_values[param_name] = np.arange(start, stop, step)

    # Determine the shape of the results array
    shape = tuple(len(values) for values in param_values.values())
    results = np.zeros(shape)

    # Generate all combinations of parameter values
    param_combinations = np.array(np.meshgrid(*param_values.values())).T.reshape(-1, len(param_ranges))

    for i, combination in enumerate(param_combinations):
        kwargs.update({param_name: value for param_name, value in zip(param_ranges.keys(), combination)})
        index = tuple(np.searchsorted(param_values[param_name], value)
                      for param_name, value in zip(param_ranges.keys(), combination))
        # positive values for buying
        results[index] = get_buying_diff(**kwargs)

    return {"results": results, "param_values": param_values}


