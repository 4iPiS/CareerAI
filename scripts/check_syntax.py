import ast, sys
try:
    with open('app/services/recommender.py', encoding='utf-8') as f:
        ast.parse(f.read())
    print('Syntax OK')
except SyntaxError as e:
    print(f'Syntax Error: {e}')
    sys.exit(1)
