from decimal import Decimal
import os
from dotenv import load_dotenv
from ofxparse import OfxParser
import psycopg2

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def processar_ofx_e_salvar():
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

  try:
    if not DATABASE_URL:
      raise ValueError("A variável DATABASE_URL não foi encontrada no .env!")

    conexao = psycopg2.connect(DATABASE_URL)
    cursor = conexao.cursor()

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id SERIAL PRIMARY KEY,
                data_movimentacao DATE,
                valor NUMERIC(15,2),
                descricao VARCHAR(255)
            );
        """)

    inseridos = 0
    duplicados = 0

    for t in transacoes:
      data_mov = t.date.date()
      valor_mov = Decimal(str(t.amount))
      desc_mov = t.memo

      cursor.execute(
          """
                SELECT id FROM movimentacoes 
                WHERE data_movimentacao = %s 
                  AND valor = %s 
                  AND descricao = %s;
            """,
          (data_mov, valor_mov, desc_mov),
      )

      if cursor.fetchone() is None:
        cursor.execute(
            """
                    INSERT INTO movimentacoes (data_movimentacao, valor, descricao)
                    VALUES (%s, %s, %s);
                """,
            (data_mov, valor_mov, desc_mov),
        )
        inseridos += 1
      else:
        duplicados += 1

    conexao.commit()
    print("\n[SUCESSO] Integração com NeonDB (PostgreSQL) concluída!")
    print(f"-> Registros novos inseridos       : {inseridos}")
    print(f"-> Registros ignorados (duplicados): {duplicados}")

  except Exception as erro:
    print(f"\n[ERRO] Falha ao conectar ou salvar no PostgreSQL: {erro}")

  finally:
    if "cursor" in locals() and cursor:
      cursor.close()
    if "conexao" in locals() and conexao:
      conexao.close()


if __name__ == "__main__":
  processar_ofx_e_salvar()