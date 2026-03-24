# Question 1: Create a for loop that counts from 0 to 10, and prints odd numbers to the screen. Use the skeleton below:

for i in range(1, 11):
    if i % 2:
        print(i)

# Question 2: Create a while loop that counts from 0 to 10, and prints odd numbers to the screen. Use the skeleton below:

x = 1
while x < 11:
    if x % 2 == 0:
        print(x)
    x+=1 

 
# Question 3: Create a program with a for loop and a break statement. 
# The program should iterate over characters in an email address, 
# exit the loop when it reaches the @ symbol, #  and print the part before @ on one line. Use the skeleton below:

for ch in "john.smith@pythoninstitute.org":
    if ch == "@":
      break
    print(ch, end="")

# Question 4: Create a program with a for loop and a continue statement. 
# The program should iterate over a string of digits, 
# replace each 0 with x, and print the modified string to the screen. 
# Use the skeleton below:

for digit in "0165031806510":
    if digit == "0":
        print("x", end=("")) # Line of code.
        continue # Line of code.
    print(digit, end="") # Line of code.
 

# Question 5: What is the output of the following code?

n = 3
 
while n > 0:         
    print(n + 1)    # 3 + 1 ;
    n -= 1          # 3 - 1 , 2 - 1 , 1 - 1 ; 
else:
    print(n)
 # OUTPUT == 4 3 2 0 

# Question 6: What is the output of the following code?

n = range(4) # 0 1 2 3 
 
for num in n:
    print(num - 1) # 0 -1 , 1 - 1 , 2 - 1 , 3 - 1 
else:
    print(num) # type: ignore # 3 ,  pois o else esta fora do loop for
 

# Question 7: What is the output of the following code?

for i in range(0, 6, 3):
    print(i) # OUTPUT == 3 

