from decimal import Decimal
import os
from tkinter import Tk, filedialog
from dotenv import load_dotenv
from ofxparse import OfxParser
import psycopg2

# Carrega a URL do NeonDB do arquivo .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def classificar_lancamento(descricao: str, valor: Decimal) -> str:
  """Classifica o tipo de lançamento conforme a descrição do extrato."""
  desc = descricao.upper()

  if "ENERGIA" in desc or "LUZ" in desc:
    return "Energia Elétrica"
  elif (
      "INTERNET" in desc
      or "TELEFONE" in desc
      or "CLOUD" in desc
      or "ASSINATURA" in desc
  ):
    return "Gasto de Telefone / Internet"
  elif "ALUGUEL" in desc:
    return "Aluguel / Imóvel"
  elif "FOLHA" in desc or "SALARIO" in desc:
    return "Folha de Pagamento"
  elif "TI" in desc or "EQUIPAMENTO" in desc:
    return "Equipamentos de TI"
  elif "MATERIAL" in desc or "LIMPEZA" in desc or "ESCRITORIO" in desc:
    return "Material de Escritório / Limpeza"
  elif "VEICULO" in desc or "MANUTENCAO" in desc or "ESTACIONAMENTO" in desc:
    return "Despesas com Veículos"
  elif valor > 0 or "RECEBIMENTO" in desc or "CLIENTE" in desc or "PIX" in desc:
    return "Receita de Clientes"
  else:
    return "Outros"


def selecionar_arquivo_ofx() -> str:
  """Abre a janela do Windows para o usuário escolher o arquivo .ofx."""
  root = Tk()
  root.withdraw()  
  root.attributes("-topmost", True)  #

  caminho = filedialog.askopenfilename(
      title="Selecione o arquivo extrato.ofx",
      filetypes=[("Arquivos OFX", "*.ofx"), ("Todos os arquivos", "*.*")],
  )
  root.destroy()
  return caminho


def processar_ofx_e_salvar():
  print("Selecione o arquivo .ofx na janela que se abriu...")
  caminho_arquivo = selecionar_arquivo_ofx()

  if not caminho_arquivo:
    print(
        "Nenhum arquivo selecionado na janela. Usando 'extrato.ofx' da pasta"
        " local..."
    )
    caminho_arquivo = "extrato.ofx"

  with open(caminho_arquivo, "rb") as arquivo:
    ofx = OfxParser.parse(arquivo)

  transacoes = ofx.account.statement.transactions

  entradas = Decimal("0.00")
  saidas = Decimal("0.00")
  quantidade_total = len(transacoes)

  print("=" * 60)
  print("                     EXTRATO BANCÁRIO                     ")
  print("=" * 60)

  for t in transacoes:
    valor = Decimal(str(t.amount))
    categoria = classificar_lancamento(t.memo, valor)

    if valor > 0:
      entradas += valor
    else:
      saidas += valor

    print(f"Data          : {t.date.strftime('%d/%m/%Y')}")
    print(f"Valor         : R$ {valor:.2f}")
    print(f"Descrição     : {t.memo}")
    print(f"Classificação : {categoria}")
    print("-" * 60)

  saldo = entradas + saidas

  print("\n" + "=" * 60)
  print("                     RESUMO FINANCEIRO                    ")
  print("=" * 60)
  print(f"Total de Movimentações : {quantidade_total}")
  print(f"Total de Entradas      : R$ {entradas:.2f}")
  print(f"Total de Saídas        : R$ {saidas:.2f}")
  print(f"Saldo Calculado        : R$ {saldo:.2f}")
  print("=" * 60)

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
                descricao VARCHAR(255),
                categoria VARCHAR(100)
            );
        """)

    cursor.execute("""
            ALTER TABLE movimentacoes 
            ADD COLUMN IF NOT EXISTS categoria VARCHAR(100);
        """)

    inseridos = 0
    atualizados = 0
    duplicados = 0

    for t in transacoes:
      data_mov = t.date.date()
      valor_mov = Decimal(str(t.amount))
      desc_mov = t.memo
      cat_mov = classificar_lancamento(desc_mov, valor_mov)

      cursor.execute(
          """
                SELECT id, categoria FROM movimentacoes 
                WHERE data_movimentacao = %s 
                  AND valor = %s 
                  AND descricao = %s;
            """,
          (data_mov, valor_mov, desc_mov),
      )

      registro = cursor.fetchone()

      if registro is None:
        cursor.execute(
            """
                    INSERT INTO movimentacoes (data_movimentacao, valor, descricao, categoria)
                    VALUES (%s, %s, %s, %s);
                """,
            (data_mov, valor_mov, desc_mov, cat_mov),
        )
        inseridos += 1
      else:
        if registro[1] is None or registro[1] != cat_mov:
          cursor.execute(
              """
                        UPDATE movimentacoes SET categoria = %s WHERE id = %s;
                    """,
              (cat_mov, registro[0]),
          )
          atualizados += 1
        else:
          duplicados += 1

    conexao.commit()
    print("\n[SUCESSO] Integração com PostgreSQL (NeonDB) concluída!")
    print(f"-> Registros novos inseridos             : {inseridos}")
    print(f"-> Registros atualizados com categoria   : {atualizados}")
    print(f"-> Registros ignorados (duplicados)      : {duplicados}")

  except Exception as erro:
    print(f"\n[ERRO] Falha ao conectar ou salvar no PostgreSQL: {erro}")

  finally:
    if "cursor" in locals() and cursor:
      cursor.close()
    if "conexao" in locals() and conexao:
      conexao.close()


if __name__ == "__main__":
  processar_ofx_e_salvar()