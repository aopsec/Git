# Exercise 4. String Slicing and Substring Removal
# Practice Problem: Write a function to remove characters from a string starting from index 0 up to n and return a new string.

# Exercise Purpose: This exercise demonstrates how to truncate data strings, a common data-cleaning task.

# Given Input:

# remove_chars("pynative", 4)
# remove_chars("pynative", 2)
# Expected Output:

# tive
# native

string = "pynative"

def remove_chars (string,n):
    remove=string[n:]
    return remove

print(remove_chars("pynative", 4))
print(remove_chars("pynative", 2))
