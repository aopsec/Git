#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 6 – PPVI
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
#   3. Use sua criatividade, elabore o problema (o enunciado) de um problema que usa função e resolva o 
#      problema proposto, ou seja, faça a implementação da função def e da função principal (main).
#   ----------------------------------------------------------------------------------------------------
#
#   PROBLEMA: Validador de Sequência Fibonacci
#   Enunciado: Dado um número inteiro positivo N, validar se N é um número que pertence à sequência
#   de Fibonacci. Implementar uma função que verifica essa condição e retorna True ou False.
#   Adicionalmente, exibir os N primeiros números da sequência.
#
#   Exemplo de entrada: 21
#   Saída esperada:
#     21 é um número de Fibonacci: True
#     Os 10 primeiros números de Fibonacci: [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
#
#   ----------------------------------------------------------------------------------------------------

def is_fibonacci(num):
    """
    Verifica se um número inteiro é parte da sequência de Fibonacci.
    
    Args:
        num (int): Número a ser validado
        
    Returns:
        bool: True se num é um número de Fibonacci, False caso contrário
    """
    if num < 1:
        return False
    
    a, b = 0, 1
    while b < num:
        a, b = b, a + b
    
    return b == num


def generate_fibonacci(count):
    """
    Gera os primeiros 'count' números da sequência de Fibonacci.
    
    Args:
        count (int): Quantidade de números a gerar
        
    Returns:
        list: Lista contendo os primeiros 'count' números de Fibonacci
    """
    if count <= 0:
        return []
    
    sequence = []
    a, b = 1, 1
    
    for _ in range(count):
        sequence.append(a)
        a, b = b, a + b
    
    return sequence


def main():
    """Função principal que executa o programa."""
    print("\n" + "="*60)
    print("VALIDADOR DE SEQUÊNCIA FIBONACCI")
    print("="*60 + "\n")
    
    try:
        num = int(input("Digite um número inteiro positivo: "))
        
        if num < 0:
            print("\nErro: Digite um número positivo.\n")
            return
        
        is_fib = is_fibonacci(num)
        fib_sequence = generate_fibonacci(10)
        
        print(f"\n{num} é um número de Fibonacci: {is_fib}")
        print(f"Os 10 primeiros números de Fibonacci: {fib_sequence}")
        
        if is_fib:
            position = fib_sequence.index(num) + 1
            print(f"Posição na sequência: {position}º termo\n")
        else:
            print()
        
    except ValueError:
        print("\nErro: Digite um número inteiro válido.\n")


if __name__ == "__main__":
    main()