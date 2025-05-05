import pandas as pd
import numpy as np

def yearly_incrementing(initial_val, interest, years):
    # calculates rent with 1 year lag to home interest (comment from original)
    # Behavior: value is constant for 12 months, then increments.
    val = initial_val
    vals = []
    for i in range(years * 12):
        if i != 0 and i % 12 == 0:
            val = val * (1 + interest)
        vals.append(val)
    return vals

def cumulative_sum(series):
    return series.cumsum()

def get_monthly_amortization_details(
        loan_principal, monthly_p_i_payment, monthly_loan_interest_rate, loan_term_years, total_years_sim):
    
    loan = loan_principal
    interests_paid = []
    principals_paid = []
    remaining_balances = []
    
    num_loan_payments = loan_term_years * 12

    for i in range(total_years_sim * 12):
        if i < num_loan_payments and loan > 0:
            interest_for_month = loan * monthly_loan_interest_rate
            
            principal_for_month = monthly_p_i_payment - interest_for_month
            
            if loan + interest_for_month <= monthly_p_i_payment : # Final payment might be smaller
                principal_for_month = loan
                interest_for_month = loan * monthly_loan_interest_rate # Interest on remaining
                # actual_payment_this_month = loan + interest_for_month # This would be the true final payment
                # For simplicity, assume monthly_p_i_payment is made, and loan reduces.
                # If monthly_p_i_payment overpays slightly on last payment, principal_for_month might be > loan.
                if principal_for_month > loan:
                    principal_for_month = loan

            loan -= principal_for_month
            
            if loan < 0.01: # Effectively zero
                loan = 0
                # Adjust principal if it caused overpayment. Interest is based on pre-payment balance.
                if principal_for_month > (loan_principal if i == 0 else remaining_balances[-1]): # Check if principal paid exceeds previous balance
                     # This case needs careful handling if monthly_p_i_payment is not perfect
                     pass


            interests_paid.append(interest_for_month)
            principals_paid.append(principal_for_month)
            remaining_balances.append(loan)
        else:
            interests_paid.append(0)
            principals_paid.append(0)
            remaining_balances.append(0) # Loan paid off
            
    return interests_paid, principals_paid, remaining_balances


def get_data(total_years=45,
             initial_rent=1500,
             home_price=800000,
             down_payment_perc=0.20,
             loan_term_years=30,
             loan_interest=0.065,
             property_tax_rate=0.0105,
             stock_interest=.11,
             home_value_interest=.054,
             ):
    yearly_payments = 12 # Kept from original, used in mortgage calc indirectly

    monthly_stock_interest = (1 + stock_interest)**(1/12) - 1
    monthly_loan_interest_rate = (1 + loan_interest)**(1/12) - 1
    # monthly_home_appreciation = (1 + home_value_interest)**(1/12) - 1 # Not directly used in revised yearly_incrementing logic check
    months = total_years * 12

    loan_principal = home_price * (1 - down_payment_perc)
    down_payment = home_price * down_payment_perc # ensure consistency
    
    num_loan_payments = loan_term_years * yearly_payments

    # Standard P&I calculation for the loan term
    if monthly_loan_interest_rate > 0:
        monthly_payment_p_i = loan_principal * (monthly_loan_interest_rate * (1 + monthly_loan_interest_rate) ** num_loan_payments) / \
                               ((1 + monthly_loan_interest_rate) ** num_loan_payments - 1)
    elif loan_principal > 0 : # No interest, just principal divided by payments
        monthly_payment_p_i = loan_principal / num_loan_payments if num_loan_payments > 0 else 0
    else: # No loan
        monthly_payment_p_i = 0

    df = pd.DataFrame({"months": list(range(months))})
    df['year'] = df['months'] / 12

    # --- Home Value and Property Tax ---
    df['home_value'] = yearly_incrementing(home_price, home_value_interest, total_years)
    df['property_tax_monthly'] = df['home_value'] * property_tax_rate / 12

    # --- Loan Details ---
    amort_interests, amort_principals, amort_balances = get_monthly_amortization_details(
        loan_principal, monthly_payment_p_i, monthly_loan_interest_rate, loan_term_years, total_years
    )
    df['monthly_interest_paid'] = amort_interests
    df['monthly_principal_paid'] = amort_principals
    df['remaining_loan_balance'] = amort_balances
    
    df['actual_monthly_p_i_payment'] = 0.0
    # P&I payments only occur during the loan term and if there's a loan
    if loan_principal > 0:
      df.loc[df['months'] < num_loan_payments, 'actual_monthly_p_i_payment'] = monthly_payment_p_i


    # --- RENTING SCENARIO ---
    df['rent_monthly'] = yearly_incrementing(initial_rent, home_value_interest, total_years)

    # Investment of the down payment amount (compounded value)
    # (df['months'] + 1) because 0-indexed months, compounding happens over the period
    df['renter_invested_down_payment_value'] = down_payment * (1 + monthly_stock_interest)**(df['months'] + 1)

    # Monthly cash flow difference for renter to invest
    # This is (Buyer's P&I + Buyer's Property Tax) - Renter's Rent
    df['renter_monthly_cash_to_invest'] = (df['actual_monthly_p_i_payment'] + df['property_tax_monthly']) - df['rent_monthly']
    
    df['renter_cumulative_investments'] = 0.0
    current_investment_balance_renter = 0.0
    for i in range(months):
        contribution = df.loc[i, 'renter_monthly_cash_to_invest']
        # Investment balance grows, then new contribution is added and grows for the next period.
        # Or, contribution added, then total grows. Let's use: (balance + contribution) * growth
        current_investment_balance_renter = (current_investment_balance_renter + contribution) * (1 + monthly_stock_interest)
        df.loc[i, 'renter_cumulative_investments'] = current_investment_balance_renter
        
    df['renting'] = df['renter_invested_down_payment_value'] + df['renter_cumulative_investments']

    # --- BUYING SCENARIO ---
    df['home_equity'] = df['home_value'] - df['remaining_loan_balance']
    # Ensure equity isn't negative if home value drops below remaining loan
    df['home_equity'] = df['home_equity'].clip(lower=0)


    df['buyer_cumulative_property_tax_paid'] = cumulative_sum(df['property_tax_monthly'])
    df['buyer_cumulative_interest_paid'] = cumulative_sum(df['monthly_interest_paid'])
    
    # Investments after mortgage is paid off
    df['buyer_monthly_cash_to_invest_post_loan'] = 0.0
    if loan_principal > 0: # Only if there was a loan to pay off
        df.loc[df['months'] >= num_loan_payments, 'buyer_monthly_cash_to_invest_post_loan'] = monthly_payment_p_i
    
    df['buyer_cumulative_investments_post_loan'] = 0.0
    current_investment_balance_buyer_post_loan = 0.0
    for i in range(months):
        contribution = df.loc[i, 'buyer_monthly_cash_to_invest_post_loan']
        current_investment_balance_buyer_post_loan = (current_investment_balance_buyer_post_loan + contribution) * (1 + monthly_stock_interest)
        df.loc[i, 'buyer_cumulative_investments_post_loan'] = current_investment_balance_buyer_post_loan

    # Buyer's Net Position:
    # Home Equity - Initial Down Payment Outlay - Cumulative Taxes Paid - Cumulative Interest Paid + Investments made after loan payoff
    df['buying'] = (df['home_equity'] - 
                       down_payment - 
                       df['buyer_cumulative_property_tax_paid'] - 
                       df['buyer_cumulative_interest_paid'] + 
                       df['buyer_cumulative_investments_post_loan'])
    
    df['diff'] = df['buying'] - df['renting']

    return df


def get_buying_diff(at_year,
                    initial_rent,
                    home_price,
                    down_payment_perc,
                    loan_term_years,
                    loan_interest,
                    property_tax_rate,
                    stock_interest,
                    home_value_interest,
                    ):
    # Ensure total_years for simulation is at least at_year
    # The get_data function needs total_years to run the simulation up to that point.
    # If at_year is, say, 10, we need to simulate for 10 years.
    df = get_data(
        total_years=at_year, # Simulate for the period we are interested in
        initial_rent=initial_rent,
        home_price=home_price,
        down_payment_perc=down_payment_perc,
        loan_term_years=loan_term_years,
        loan_interest=loan_interest,
        property_tax_rate=property_tax_rate,
        stock_interest=stock_interest,
        home_value_interest=home_value_interest)
    
    # iloc[-1] will give the value at the end of (at_year * 12 - 1)th month
    if df.empty or 'diff' not in df.columns:
        return np.nan # Or raise an error
    return df['diff'].iloc[-1]


def grid_search_buying_diff(param_ranges=None, **kwargs):
    """
    Performs a grid search over specified parameters to find the buying diff.
    (Docstring from original)
    """
    if param_ranges is None:
        param_ranges = {}

    valid_params = [
        "at_year", "initial_rent", "home_price", "down_payment_perc",
        "loan_term_years", "loan_interest", "property_tax_rate",
        "stock_interest", "home_value_interest",
    ]

    # Check that all necessary parameters are provided either as fixed or ranged
    for param_name in valid_params:
        if param_name not in kwargs and param_name not in param_ranges:
            raise ValueError(f"Parameter '{param_name}' must be specified either as a fixed value or in param_ranges.")
        if param_name in kwargs and param_name in param_ranges:
            raise ValueError(f"Parameter '{param_name}' cannot be in both kwargs (fixed) and param_ranges.")

    # Prepare parameter grids
    grid_params = []
    grid_param_names = []

    for param_name in valid_params: # Iterate in a fixed order for consistency
        if param_name in param_ranges:
            start, stop, step = param_ranges[param_name]
            values = np.arange(start, stop, step)
            if values.size == 0 and start < stop : # if step makes it empty but shouldn't be
                 values = np.array([start]) # Ensure at least start value if range is valid
            elif values.size == 0 and start >= stop: # if range itself is invalid
                 raise ValueError(f"Invalid range for {param_name}: start={start}, stop={stop}, step={step} results in empty array.")
            grid_params.append(values)
            grid_param_names.append(param_name)
        else: # Parameter is fixed from kwargs
            grid_params.append(np.array([kwargs[param_name]])) # Treat as a single-value list for meshgrid
            # grid_param_names.append(param_name) # Not part of the varying grid dimensions

    # Create meshgrid for varying parameters
    varying_param_names = [name for name in valid_params if name in param_ranges]
    varying_param_values = [p_vals for p_name, p_vals in zip(valid_params, grid_params) if p_name in param_ranges]


    if not varying_param_values: # All parameters are fixed, single calculation
        if 'at_year' not in kwargs: # at_year must be present
             raise ValueError("Parameter 'at_year' must be specified.")
        result_val = get_buying_diff(**kwargs)
        # Store results in a way that reflects param_values structure expected by caller
        # This part needs careful construction if original return format is vital for fixed params
        # For now, let's assume param_ranges is not empty if this function is used for its typical purpose
        # If param_ranges IS empty, the original code might have issues too; let's make it robust.
        results_array = np.array([result_val])
        param_values_dict = {k: np.array([v]) for k,v in kwargs.items() if k in valid_params}

    else:
        param_combinations = np.array(np.meshgrid(*varying_param_values)).T.reshape(-1, len(varying_param_names))
        
        shape = tuple(len(values) for values in varying_param_values)
        results_array = np.zeros(shape)

        # Build the param_values dictionary for the return value
        param_values_dict = {name: values for name, values in zip(varying_param_names, varying_param_values)}
        for fixed_param_name in kwargs:
             if fixed_param_name in valid_params and fixed_param_name not in param_values_dict:
                  param_values_dict[fixed_param_name] = np.array([kwargs[fixed_param_name]])


        for i, combination in enumerate(param_combinations):
            current_kwargs = kwargs.copy() # Start with fixed kwargs
            current_kwargs.update({name: value for name, value in zip(varying_param_names, combination)})
            
            # Determine index for results_array
            if results_array.ndim == 1 and len(varying_param_names) == 1: # Single varying parameter
                index = (np.searchsorted(varying_param_values[0], combination[0]),)
            elif results_array.ndim > 1 : # Multiple varying parameters
                 index = tuple(np.searchsorted(varying_param_values[j], combination[j]) for j in range(len(varying_param_names)))
            else: # Should not happen if varying_param_values is not empty
                index = ()


            results_array[index] = get_buying_diff(**current_kwargs)

    return {"results": results_array, "param_values": param_values_dict}


if __name__ == "__main__":
    # Example usage:
    pd.set_option('display.max_columns', None) # Show all columns
    pd.set_option('display.width', 200) # Wider display for DataFrame

    # --- Test 1: Default parameters, look at year 30 ---
    print("--- Test 1: Default parameters, diff at year 30 ---")
    params_test1 = {
        "at_year": 30,
        "initial_rent": 1500,
        "home_price": 800000,
        "down_payment_perc": 0.20,
        "loan_term_years": 30,
        "loan_interest": 0.065,
        "property_tax_rate": 0.0105,
        "stock_interest": 0.11,
        "home_value_interest": 0.054,
    }
    diff_at_year_30 = get_buying_diff(**params_test1)
    print(f"Difference (Buying - Renting) at year 30: {diff_at_year_30:,.0f}")
    print("\n")

    # --- Test 2: Show full DataFrame for a shorter period (e.g., 5 years) ---
    print("--- Test 2: DataFrame for first 5 years ---")
    df_5_years = get_data(
        total_years=5,
        initial_rent=1500,
        home_price=800000,
        down_payment_perc=0.20,
        loan_term_years=30, # Loan term can be longer than simulation
        loan_interest=0.065,
        property_tax_rate=0.0105,
        stock_interest=0.11,
        home_value_interest=0.054
    )
    # Select relevant columns for display
    cols_to_show = [
        'months', 'year', 'home_value', 'remaining_loan_balance', 'home_equity',
        'rent_monthly', 'renter_invested_down_payment_value', 'renter_monthly_cash_to_invest', 'renter_cumulative_investments', 'renting',
        'buyer_cumulative_property_tax_paid', 'buyer_cumulative_interest_paid', 'buyer_cumulative_investments_post_loan', 'buying',
        'diff'
    ]
    print(df_5_years[cols_to_show].round(0))
    print("\n")

    # --- Test 3: Grid search example ---
    print("--- Test 3: Grid search over home_value_interest ---")
    grid_params_test = {
        "at_year": 30, # Fixed
        "initial_rent": 1500, # Fixed
        "home_price": 800000, # Fixed
        "down_payment_perc": 0.20, # Fixed
        "loan_term_years": 30, # Fixed
        "loan_interest": 0.065, # Fixed
        "property_tax_rate": 0.0105, # Fixed
        "stock_interest": 0.11, # Fixed
    }
    search_results = grid_search_buying_diff(
        param_ranges={"home_value_interest": (0.03, 0.07, 0.01)}, # Varying home appreciation
        **grid_params_test
    )
    print("Grid search results (home_value_interest vs. diff):")
    for hvi, diff_val in zip(search_results['param_values']['home_value_interest'], search_results['results']):
        print(f"Home Value Interest: {hvi:.2%}, Buying Advantage: {diff_val:,.0f}")


if __name__ == "__main__":
    df = get_data()

    print(df[df['months']%12==0]['buying'])
    print(df[df['months']%12==0])        