import pandas as pd
import numpy as np

def get_debt_data(
        initial_loan_principal,
        fixed_monthly_payment_amount, # The payment amount during the loan term
        monthly_loan_rate,
        total_simulation_months,    # e.g., total_years * 12
        loan_payment_term_months    # e.g., loan_term_years * 12
        ):
    current_loan_balance = initial_loan_principal
    debt_values_over_time = []
    interest_paid_over_time = []
    for month_index in range(total_simulation_months):
        if current_loan_balance <= 0: # Loan already paid off
            debt_values_over_time.append(0)
            interest_paid_over_time.append(0)
            current_loan_balance = 0 # Ensure it stays 0 for subsequent months
            continue

        interest_for_month = current_loan_balance * monthly_loan_rate
        interest_paid_over_time.append(interest_for_month)

        payment_made_this_month = 0
        # Check if payments are still being made in the current month
        if month_index < loan_payment_term_months:
            payment_made_this_month = fixed_monthly_payment_amount

        current_loan_balance += interest_for_month      # Add interest
        current_loan_balance -= payment_made_this_month # Subtract payment

        if current_loan_balance < 0: # Loan paid off (or overpaid)
            current_loan_balance = 0

        debt_values_over_time.append(current_loan_balance)
    return debt_values_over_time, interest_paid_over_time

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

def calculate_growth_repeated_investments(investments: pd.Series, rate: float) -> pd.Series:
    acc = np.zeros(len(investments))
    acc[0] = investments.iloc[0]
    for i in range(1, len(investments)):
        acc[i] = acc[i-1] * (1 + rate) + investments.iloc[i]
    return pd.Series(acc, index=investments.index)

def get_data(total_years=45,
             initial_rent=1500,
             home_price=800000,
             down_payment_perc=0.20,
             loan_term_years=30,
             loan_interest=0.065,
             property_tax_rate=0.0105,
             stock_interest=.11,
             home_value_interest=.054,
             home_upkeep_percent = .01,
             tenant_rent = 0
             ):

    yearly_payments=12

    monthly_loan_interest_rate = (1+loan_interest)**(1/12) - 1
    months = total_years * 12

    loan_principal = home_price * (1-down_payment_perc)
    down_payment = home_price - loan_principal
    payments = loan_term_years * yearly_payments
    monthly_payment = loan_principal * (monthly_loan_interest_rate * (1 + monthly_loan_interest_rate) ** payments) / ((1 + monthly_loan_interest_rate) ** payments - 1)

    monthly_stock_interest = (1+stock_interest)**(1/12) - 1
    monthly_home_appreciation = (1+home_value_interest)**(1/12) - 1

    df = pd.DataFrame({"months": list(range(months))})
    df['year'] = df['months'] / 12

    df['home_value'] = yearly_incrementing(home_price, home_value_interest, total_years)
    df['property_tax_monthly'] = df['home_value'] * property_tax_rate / 12
    df['home_upkeep_monthly'] = df['home_value'] * home_upkeep_percent / 12

    df['mortgage_payment'] = monthly_payment
    df['mortgage_payment'] = df['months'].apply(lambda month: monthly_payment if month <= loan_term_years * 12 else 0)

    df['down_payment']  = 0
    df.loc[0, 'down_payment'] += down_payment

    num_loan_payment_months = loan_term_years * 12 # Or use your existing 'payments' variable: loan_term_years * yearly_payments

    df['remaining_debt'], df['monthly_interest_owed'] = get_debt_data(
        loan_principal,
        monthly_payment,
        monthly_loan_interest_rate,
        months,
        num_loan_payment_months,
    )

    df['net_worth_with_home'] = df['home_value'] - df['remaining_debt']

    df['tenant_rent'] = yearly_incrementing(tenant_rent, home_value_interest, total_years)
    df['paid_towards_home'] = df['down_payment'] + df['mortgage_payment'] + df['property_tax_monthly'] + df['home_upkeep_monthly'] - df['tenant_rent']

    #####################
    # RENT
    #####################

    df['rent'] = yearly_incrementing(initial_rent, home_value_interest, total_years)

    df['excess_available_to_invest_monthly_renting'] = df['paid_towards_home'] - df['rent']

    df['cumulative_invested_renting'] = calculate_growth_repeated_investments(df['excess_available_to_invest_monthly_renting'],
                                                                              monthly_stock_interest)

    df['net_worth_renting'] =  df['cumulative_invested_renting']

    CAPITAL_GAINS_TAX_RATE = .15
    # not all of investments would be subject to capital gains tax, but in a world where buy v renting doesnt affect maxing out retirement
    # accounts this is a reasonable assumption i think
    df['capital_gains_tax'] = df['net_worth_renting'] * (CAPITAL_GAINS_TAX_RATE)
    df['effective_net_worth_renting'] = df['net_worth_renting'] - df['capital_gains_tax']
    REALTOR_COST = .06 # percent
    df['realtor_fees_if_selling'] = df['net_worth_with_home'] * (REALTOR_COST)
    df['effective_net_worth_with_home'] = df['net_worth_with_home'] - df['realtor_fees_if_selling']

    return df
