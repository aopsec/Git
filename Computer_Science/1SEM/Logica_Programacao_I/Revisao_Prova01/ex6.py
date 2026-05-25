# Exercise 6. Calculating Factorial with a Loop
# Practice Problem: Write a program that calculates the factorial of a given number (e.g., 5!) using a for loop.

# Exercise Purpose: This exercise explores “Mathematical Accumulation.” A factorial (e.g., 5! = 5*4*3*2*1) 
# requires you to maintain a running product across multiple iterations, which is a core pattern in scientific computing.
# Given Input: number = 5

# Expected Output: The factorial of 5 is 120



def fatorial(x):
    result = 1
    for i in range(1,x+1):
        result *= i
    return result

print(f"The factorial of 5 is {fatorial(5)}")