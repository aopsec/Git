# Exercise 1. Arithmetic Product and Conditional Logic
# Practice Problem: Write a Python function that accepts two integer numbers. 
# If the product of the two numbers is less than or equal to 1000, return their product; otherwise, return their sum.

# Exercise Purpose: Learn basic control flow and the use of if-else statements. Understand how code decisions change output based on a mathematical threshold.

# Given Input:

# Case 1: number1 = 20, number2 = 30
# Case 2: number1 = 40, number2 = 30
# Expected Output:

# The result is 600
# The result is 70

def num(num01,num02):   
    if num01*num02 <= 1000:
        print(f"The result is {num01*num02}")
        return 
    else:
        print(f"The result is {num01+num02}")
        return 

num(num01=20,num02=30)

num(num01=40,num02=30)