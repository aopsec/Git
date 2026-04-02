def is_year_leap(year):
    if year % 4 != 0:
        return False
    elif year % 100 != 0:
        return True
    elif year % 400 != 0:
        return False
    else:
        return True


def days_in_month(year, month):
    if year < 1582 or month < 1 or month > 12: # Teste Argumentos
        return None
    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and is_year_leap(year): # Fev em ano 366 
        return 29
    return months[month -1]

def day_of_year(year , month , day):
    days = 0
    for m in range(1,month):
        md = days_in_month(year, m)
        days += md
    if md is None:
        return None
    if day >=1 and day <= md:
        return day + days
    else:
        return None
print(day_of_year(2000, 12, 31))