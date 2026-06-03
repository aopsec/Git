
Section 1 / 10

# Bourne Again Shell

---

[Bash](https://en.wikipedia.org/wiki/Bash_\(Unix_shell\)) is the scripting language we use to communicate with Unix-based OS and give commands to the system. Since May 2019, Windows provides a [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/about) that allows us to use `Bash` in a Windows environment. It is essential to master the language to work efficiently with it. The main difference between scripting and programming languages is that we don't need to compile the code to execute the scripting language, as opposed to programming languages.

As penetration testers, we must be able to work with any operating system, whether it is Windows or Unix-based. Efficiency depends mainly on the knowledge of the systems, especially in the privilege escalation field. On Unix-based systems, it is essential to learn how to use the terminal, filter data, and automate these processes. Especially in large Unix-based enterprise networks, we will have to deal with large amounts of data. We have to sort and filter out accordingly to determine potential gaps and information as fast as possible.

It is also essential to learn how to combine several commands and work with individual results. This is where scripting comes in, increasing our speed and efficiency. Like a programming language, a scripting language has almost the same structure, which can be divided into:

- `Input` & `Output`
- `Arguments`, `Variables` & `Arrays`
- `Conditional execution`
- `Arithmetic`
- `Loops`
- `Comparison operators`
- `Functions`

It is often common to automate some processes not to repeat them all the time or process and filter a large amount of information. In general, a script does not create a process, but it is executed by the interpreter that executes the script, in this case, the `Bash`. To execute a script, we have to specify the interpreter and tell it which script it should process. Such a call looks like this:

#### Script Execution - Examples

        shellsession
`aopsec@htb[/htb]$ bash script.sh <optional arguments>`

        shellsession
`aopsec@htb[/htb]$ sh script.sh <optional arguments>`

        shellsession
`aopsec@htb[/htb]$ ./script.sh <optional arguments>`

Let us look at such a script and see how they can be created to get specific results. If we execute this script and specify a domain, we see what information this script provides.

#### CIDR.sh

        shellsession
`aopsec@htb[/htb]$ ./CIDR.sh inlanefreight.com Discovered IP address(es): 165.22.119.202 Additional options available:     1) Identify the corresponding network range of target domain.    2) Ping discovered hosts.    3) All checks.    *) Exit. Select your option: 3 NetRange for 165.22.119.202: NetRange:       165.22.0.0 - 165.22.255.255 CIDR:           165.22.0.0/16 Pinging host(s): 165.22.119.202 is up. 1 out of 1 hosts are up.`

Now let us look at that script in detail and read it line by line in the best possible way. In the next sections, we will look at and analyze all the parts of this script.

#### CIDR.sh

        bash
`#!/bin/bash # Check for given arguments if [ $# -eq 0 ] then     echo -e "You need to specify the target domain.\n"    echo -e "Usage:"    echo -e "\t$0 <domain>"    exit 1 else     domain=$1 fi # Identify Network range for the specified IP address(es) function network_range {     for ip in $ipaddr    do        netrange=$(whois $ip | grep "NetRange\|CIDR" | tee -a CIDR.txt)        cidr=$(whois $ip | grep "CIDR" | awk '{print $2}')        cidr_ips=$(prips $cidr)        echo -e "\nNetRange for $ip:"        echo -e "$netrange"    done } # Ping discovered IP address(es) function ping_host {     hosts_up=0    hosts_total=0         echo -e "\nPinging host(s):"    for host in $cidr_ips    do        stat=1        while [ $stat -eq 1 ]        do            ping -c 2 $host > /dev/null 2>&1            if [ $? -eq 0 ]            then                echo "$host is up."                ((stat--))                ((hosts_up++))                ((hosts_total++))            else                echo "$host is down."                ((stat--))                ((hosts_total++))            fi        done    done         echo -e "\n$hosts_up out of $hosts_total hosts are up." } # Identify IP address of the specified domain hosts=$(host $domain | grep "has address" | cut -d" " -f4 | tee discovered_hosts.txt) echo -e "Discovered IP address:\n$hosts\n" ipaddr=$(host $domain | grep "has address" | cut -d" " -f4 | tr "\n" " ") # Available options echo -e "Additional options available:" echo -e "\t1) Identify the corresponding network range of target domain." echo -e "\t2) Ping discovered hosts." echo -e "\t3) All checks." echo -e "\t*) Exit.\n" read -p "Select your option: " opt case $opt in     "1") network_range ;;    "2") ping_host ;;    "3") network_range && ping_host ;;    "*") exit 0 ;; esac`

---

As we can see, we have commented here several parts of the script into which we can split it.

1. Check for given arguments
2. Identify network range for the specified IP address(es)
3. Ping discovered IP address(es)
4. Identify IP address(es) of the specified domain
5. Available options

---

#### 1. Check for given arguments

In the first part of the script, we have an if-else statement that checks if we have specified a domain representing the target company.

---

#### 2. Identify network range for the specified IP address(es)

Here we have created a function that makes a "whois" query for each IP address and displays the line for the reserved network range, and stores it in the CIDR.txt.

---

#### 3. Ping discovered IP address(es)

This additional function is used to check if the found hosts are reachable with the respective IP addresses. With the For-Loop, we ping every IP address in the network range and count the results.

---

#### 4. Identify IP address(es) of the specified domain

As the first step in this script, we identify the IPv4 address of the domain returned to us.

---

#### 5. Available Options

Then we decide which functions we want to use to find out more information about the infrastructure.



Section 2 / 10

[Go to Questions](https://academy.hackthebox.com/app/module/21/section/132#questions-list)

# Conditional Execution

---

Conditional execution allows us to control the flow of our script by reaching different conditions. This function is one of the essential components. Otherwise, we could only execute one command after another.

When defining various conditions, we specify which functions or sections of code should be executed for a specific value. If we reach a specific condition, only the code for that condition is executed, and the others are skipped. As soon as the code section is completed, the following commands will be executed outside the conditional execution. Let us look at the first part of the script again and analyze it.

#### Script.sh

        bash
`#!/bin/bash # Check for given argument if [ $# -eq 0 ] then     echo -e "You need to specify the target domain.\n"    echo -e "Usage:"    echo -e "\t$0 <domain>"    exit 1 else     domain=$1 fi <SNIP>`

In summary, this code section works with the following components:

- `#!/bin/bash` - Shebang.
- `if-else-fi` - Conditional execution.
- `echo` - Prints specific output.
- `$#` / `$0` / `$1` - Special variables.
- `domain` - Variables.

The conditions of the conditional executions can be defined using variables (`$#`, `$0`, `$1`, `domain`), values (`0`), and strings, as we will see in the next examples. These values are compared with the `comparison operators` (`-eq`) that we will look at in the next section.

---

## Shebang

The shebang line is always at the top of each script and always starts with "`#!`". This line contains the path to the specified interpreter (`/bin/bash`) with which the script is executed. We can also use Shebang to define other interpreters like Python, Perl, and others.

        python
`#!/usr/bin/env python`

        perl
`#!/usr/bin/env perl`

---

## If-Else-Fi

One of the most fundamental programming tasks is to check different conditions to deal with these. Checking of conditions usually has two different forms in programming and scripting languages, the `if-else condition` and `case statements`. In pseudo-code, the if condition means the following:

#### Pseudo-Code

        bash
`if [ the number of given arguments equals 0 ] then     Print: "You need to specify the target domain."    Print: "<empty line>"    Print: "Usage:"    Print: "   <name of the script> <domain>"    Exit the script with an error else     The "domain" variable serves as the alias for the given argument  finish the if-condition`

By default, an `If-Else` condition can contain only a single "`If`", as shown in the next example.

#### If-Only.sh

        bash
`#!/bin/bash value=$1 if [ $value -gt "10" ] then         echo "Given argument is greater than 10." fi`

#### If-Only.sh - Execution

        shellsession
`aopsec@htb[/htb]$ bash if-only.sh 5`

        shellsession
`aopsec@htb[/htb]$ bash if-only.sh 12 Given argument is greater than 10.`

---

When adding `Elif` or `Else`, we add alternatives to treat specific values or statuses. If a particular value does not apply to the first case, it will be caught by others.

#### If-Elif-Else.sh

        bash
`#!/bin/bash value=$1 if [ $value -gt "10" ] then     echo "Given argument is greater than 10." elif [ $value -lt "10" ] then     echo "Given argument is less than 10." else     echo "Given argument is not a number." fi`

#### If-Elif-Else.sh - Execution

        shellsession
`aopsec@htb[/htb]$ bash if-elif-else.sh 5 Given argument is less than 10.`

        shellsession
`aopsec@htb[/htb]$ bash if-elif-else.sh 12 Given argument is greater than 10.`

        shellsession
`aopsec@htb[/htb]$ bash if-elif-else.sh HTB if-elif-else.sh: line 5: [: HTB: integer expression expected if-elif-else.sh: line 8: [: HTB: integer expression expected Given argument is not a number.`

---

We could extend our script and specify several conditions. This could look something like this:

#### Several Conditions - Script.sh

        bash
`#!/bin/bash # Check for given argument if [ $# -eq 0 ] then     echo -e "You need to specify the target domain.\n"    echo -e "Usage:"    echo -e "\t$0 <domain>"    exit 1 elif [ $# -eq 1 ] then     domain=$1 else     echo -e "Too many arguments given."    exit 1 fi <SNIP>`

Here we define another condition (`elif [<condition>];then`) that prints a line telling us (`echo -e "..."`) that we have given more than one argument and exits the program with an error (`exit 1`).

---

---

## Exercise Script

        bash
`#!/bin/bash # Count number of characters in a variable: #     echo $variable | wc -m # Variable to encode var="nef892na9s1p9asn2aJs71nIsm" for counter in {1..40} do         var=$(echo $var | base64) done`

### Create an "If-Else" condition in the "For"-Loop of the "Exercise Script" that prints you the number of characters of the 35th generated value of the variable "var". Submit the number as the answer.1


Section 3 / 10

[Go to Questions](https://academy.hackthebox.com/app/module/21/section/125#questions-list)

# Arguments, Variables, and Arrays

---

## Arguments

The advantage of bash scripts is that we can always pass up to 9 arguments (`$0`-`$9`) to the script without assigning them to variables or setting the corresponding requirements for these. `9 arguments` because the first argument `$0` is reserved for the script. As we can see here, we need the dollar sign (`$`) before the name of the variable to use it at the specified position. The assignment would look like this in comparison:

        shellsession
`aopsec@htb[/htb]$ ./script.sh ARG1 ARG2 ARG3 ... ARG9        ASSIGNMENTS:       $0      $1   $2   $3 ...   $9`

This means that we have automatically assigned the corresponding arguments to the predefined variables in this place. These variables are called special variables. These special variables serve as placeholders. If we now look at the code section again, we will see where and which arguments have been used.

#### CIDR.sh

        bash
`#!/bin/bash # Check for given argument if [ $# -eq 0 ] then     echo -e "You need to specify the target domain.\n"    echo -e "Usage:"    echo -e "\t$0 <domain>"    exit 1 else     domain=$1 fi <SNIP>`

There are several ways how we can execute our script. However, we must first set the script's execution privileges before executing it with the interpreter defined in it.

#### CIDR.sh - Set Execution Privileges

        shellsession
`aopsec@htb[/htb]$ chmod +x cidr.sh`

#### CIDR.sh - Execution without Arguments

        shellsession
`aopsec@htb[/htb]$ ./cidr.sh You need to specify the target domain. Usage:     cidr.sh <domain>`

#### CIDR.sh - Execution without Execution Permissions

        shellsession
`aopsec@htb[/htb]$ bash cidr.sh You need to specify the target domain. Usage:     cidr.sh <domain>`

---

## Special Variables

Special variables use the [Internal Field Separator](https://bash.cyberciti.biz/guide/$IFS) (`IFS`) to identify when an argument ends and the next begins. Bash provides various special variables that assist while scripting. Some of these variables are:

|**Special Variable**|**Description**|
|---|---|
|`$#`|This variable holds the number of arguments passed to the script.|
|`$@`|This variable can be used to retrieve the list of command-line arguments.|
|`$n`|Each command-line argument can be selectively retrieved using its position. For example, the first argument is found at `$1`.|
|`$$`|The process ID of the currently executing process.|
|`$?`|The exit status of the script. This variable is useful to determine a command's success. The value 0 represents successful execution, while 1 is a result of a failure.|

Of the ones shown above, we have 3 such special variables in our `if-else` condition.

|**Special Variable**|**Description**|
|---|---|
|`$#`|In this case, we need just one variable that needs to be assigned to the `domain` variable. This variable is used to specify the target we want to work with. If we provide just an FQDN as the argument, the `$#` variable will have a value of `1`.|
|`$0`|This special variable is assigned the name of the executed script, which is then shown in the "`Usage:`" example.|
|`$1`|Separated by a space, the first argument is assigned to that special variable.|

---

## Variables

We also see at the end of the if-else loop that we assign the value of the first argument to the variable called "`domain`". The assignment of variables takes place without the dollar sign (`$`). The dollar sign is only intended to allow this variable's corresponding value to be used in other code sections. When assigning variables, there must be no spaces between the names and values.

        bash
`<SNIP> else     domain=$1 fi <SNIP>`

In contrast to other programming languages, there is no direct differentiation and recognition between the types of variables in Bash like "`strings`," "`integers`," and "`boolean`." All contents of the variables are treated as string characters. Bash enables arithmetic functions depending on whether only numbers are assigned or not. It is important to note when declaring variables that they do `not` contain a `space`. Otherwise, the actual variable name will be interpreted as an internal function or a command.

#### Declaring a Variable - Error

        shellsession
`aopsec@htb[/htb]$ variable = "this will result with an error." command not found: variable`

#### Declaring a Variable - Without an Error

        shellsession
`aopsec@htb[/htb]$ variable="Declared without an error." aopsec@htb[/htb]$ echo $variable Declared without an error.`

---

## Arrays

There is also the possibility of assigning several values to a single variable in Bash. This can be beneficial if we want to scan multiple domains or IP addresses. These variables are called `arrays` that we can use to store and process an ordered sequence of specific type values. `Arrays` identify each stored entry with an `index` starting with `0`. When we want to assign a value to an array component, we do so in the same way as with standard shell variables. All we do is specify the field index enclosed in square brackets. The declaration for `arrays` looks like this in Bash:

#### Arrays.sh

        bash
`#!/bin/bash domains=(www.inlanefreight.com ftp.inlanefreight.com vpn.inlanefreight.com www2.inlanefreight.com) echo ${domains[0]}`

We can also retrieve them individually using the index using the variable with the corresponding index in curly brackets. Curly brackets are used for variable expansion.

        shellsession
`aopsec@htb[/htb]$ ./Arrays.sh www.inlanefreight.com`

It is important to note that single quotes (`'` ... `'`) and double quotes (`"` ... `"`) prevent the separation by a space of the individual values in the array. This means that all spaces between the single and double quotes are ignored and handled as a single value assigned to the array.

#### Arrays.sh

        bash
`#!/bin/bash domains=("www.inlanefreight.com ftp.inlanefreight.com vpn.inlanefreight.com" www2.inlanefreight.com) echo ${domains[0]}`

        shellsession
`aopsec@htb[/htb]$ ./Arrays.sh www.inlanefreight.com ftp.inlanefreight.com vpn.inlanefreight.com`

## Connect to HTB

Enable step-by-step solutions

PRO

- ## Question 1
    
    +2
    
    +30
    
    ---
    
    ### Submit the echo statement that would print "www2.inlanefreight.com" when running the last "Arrays.sh" script.