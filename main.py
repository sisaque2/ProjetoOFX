from decimal import Decimal
from ofxparse import OfxParser

# Abrindo e fazendo o parse do arquivo OFX
with open("extrato.ofx", "rb") as arquivo:
  ofx = OfxParser.parse(arquivo)

transacoes = ofx.account.statement.transactions

entradas = Decimal("0.00")
saidas = Decimal("0.00")
quantidade_total = len(transacoes)

print("=" * 45)
print("              EXTRATO BANCÁRIO               ")
print("=" * 45)

for t in transacoes:
  valor = Decimal(str(t.amount))

  # Contabiliza entradas e saídas
  if valor > 0:
    entradas += valor
  else:
    saidas += valor

  print(f"Data      : {t.date.strftime('%d/%m/%Y')}")
  print(f"Valor     : R$ {valor:.2f}")
  print(f"Descrição : {t.memo}")
  print("-" * 45)

saldo = entradas + saidas

print("\n" + "=" * 45)
print("              RESUMO FINANCEIRO              ")
print("=" * 45)
print(f"Total de Movimentações : {quantidade_total}")
print(f"Total de Entradas      : R$ {entradas:.2f}")
print(f"Total de Saídas        : R$ {saidas:.2f}")
print(f"Saldo Calculado        : R$ {saldo:.2f}")
print("=" * 45)