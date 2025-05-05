import pandas as pd

def yearly_incrementing(initial_val, interest, years):
    # calculates rent with 1 year lag to home interest
    val=initial_val
    vals = []
    for i in range(years * 12):
        if i != 0 and i%12==0:
            val = val * (1+interest)
        vals.append(val)
    return vals


def cumulative_sum(l):
    sums = []
    sum = 0
    for v in l:
        sum+=v
        sums.append(sum)
    return sums

def get_monthly_interest_owed(
        loan_principal, monthly_payment, monthly_loan_interest_rate, total_years):
    loan = loan_principal
    interest = 0
    interests = []
    for i in range(total_years*12):
        monthly_interest = loan * (monthly_loan_interest_rate)
        loan = loan + monthly_interest - monthly_payment
        if loan <= 0:
            loan = 0
        interests.append(monthly_interest)
    return interests


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
    yearly_payments=12

    monthly_stock_interest = (1+stock_interest)**(1/12) - 1
    monthly_loan_interest_rate = (1+loan_interest)**(1/12) - 1
    monthly_home_appreciation = (1+home_value_interest)**(1/12) - 1
    months = total_years * 12


    loan_principal = home_price * (1-down_payment_perc)
    down_payment = home_price - loan_principal
    payments = loan_term_years * yearly_payments
    monthly_payment = loan_principal * (monthly_loan_interest_rate * (1 + monthly_loan_interest_rate) ** payments) / ((1 + monthly_loan_interest_rate) ** payments - 1)

    
    df = pd.DataFrame(
        {"months": list(range(months))}
    )
    df['year'] = df['months'] /12

    df['home_value'] = yearly_incrementing(home_price, home_value_interest, total_years)

    df['property_tax'] = df['home_value'] * property_tax_rate/12

    # renting

    df['rent'] = yearly_incrementing(initial_rent, home_value_interest, total_years)

    df['cumulative_rent'] = cumulative_sum(df['rent'])

    df['monthly interest lost to rent'] = df['cumulative_rent'] * monthly_stock_interest

    df['invested instead of downpayment'] = down_payment * (1+monthly_stock_interest)**(df['months'])
    df['real price of rent'] = cumulative_sum(df['monthly interest lost to rent']) + df['cumulative_rent']

    df['excess_available_investing_if_renting'] = df['property_tax'] + monthly_payment - df['rent']

    df['renting available to invest'] = cumulative_sum(df['excess_available_investing_if_renting'])
    df['monthly investment return with no mortgage']= df['renting available to invest']*monthly_stock_interest
    df['cumulative investment while renting'] = cumulative_sum(df['monthly investment return with no mortgage']) + df['renting available to invest']    
    df['renting'] =df['cumulative investment while renting']  - df['real price of rent'] + df['invested instead of downpayment']
    # buying


    df['monthly_payment'] = monthly_payment
    df['monthly_payment'] = df['months'].apply(lambda month: monthly_payment if month <= loan_term_years * 12 else 0)

    df.loc[0, 'monthly_payment'] += down_payment

    df['loan_principal'] = loan_principal
    df['down_payment'] = down_payment

    df['monthly_interest_owed'] = get_monthly_interest_owed(
        loan_principal, monthly_payment, monthly_loan_interest_rate, total_years)

    df['cumulative property_tax'] = cumulative_sum(df['property_tax'])

    df['interest lost to property tax'] = df['cumulative property_tax'] * monthly_stock_interest

    df['rent'] = yearly_incrementing(initial_rent, home_value_interest, total_years)

    df['interest lost to down payment'] = df['down_payment'] * (1+monthly_stock_interest)**(df['months']) - df['down_payment']
    down_payment_interest_loss = df['interest lost to down payment']
    property_tax_interest_lost = df['interest lost to property tax']

    df['cumulative interest lost to property tax'] = cumulative_sum(df['interest lost to property tax'])
    cum_property_tax_interest_lost = df['cumulative interest lost to property tax']    

    house_money_lost = df['property_tax'] + cum_property_tax_interest_lost + down_payment_interest_loss
    df['house_money_lost'] = house_money_lost



    df['payed_toward_home'] =  cumulative_sum(df['monthly_payment'] - df['monthly_interest_owed'])

    df['home available to invest'] = monthly_payment - df['monthly_payment']
    df.loc[0, 'home available to invest'] = 0
    df['cumulative available to invest'] = cumulative_sum(df['home available to invest'])
    df['monthly investment return with no rent and no mortgage']= df['cumulative available to invest']*monthly_stock_interest
    df['cumulative investment after mortgage'] = cumulative_sum(df['monthly investment return with no rent and no mortgage']) + df['cumulative available to invest']

    df['home_owned'] = df['payed_toward_home'] * (1+monthly_home_appreciation)**(df['months'])
    df['buying'] = df['home_owned'] - house_money_lost + df['cumulative investment after mortgage'] 

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
    df = get_data(
        total_years=at_year,
        initial_rent=initial_rent,
        home_price=home_price,
        down_payment_perc=down_payment_perc,
        loan_term_years=loan_term_years,
        loan_interest=loan_interest,
        property_tax_rate=property_tax_rate,
        stock_interest=stock_interest,
        home_value_interest=home_value_interest)
    return df['diff'].iloc[-1]

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
        results[index] = get_buying_diff(**kwargs) 

    return {"results": results, "param_values": param_values}


if __name__ == "__main__":
    df = get_data()

    print(df[df['months']%12==0]['buying'])
    print(df[df['months']%12==0])