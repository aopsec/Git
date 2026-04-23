# Exercise 5. Variable Swapping (The In-Place Method)
# Practice Problem: Write a program to swap the values of two variables, a and b, without using a third temporary variable.

# Exercise Purpose: This exercise will help you learn about memory efficiency and Python’s special tuple unpacking feature. 
# In other languages like C or Java, you need a temporary variable to swap values safely. 
# In Python, you can swap values in one line without risking data loss.

# Given Input: a = 5, b = 10

# Expected Output:

# Before Swap: a = 5, b = 10
# After Swap: a = 10, b = 5


def swap (a , b):
    print(f"BeforeSwap a = {a}, b = {b}")
    a , b = b , a
    print(f"AfterSwap a = {a}, b = {b}")
    return 

swap(a=5,b=10)

