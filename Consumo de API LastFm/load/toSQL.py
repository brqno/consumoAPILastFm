from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, text, BigInteger
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import urllib.parse
import sys
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Artist(Base):
    __tablename__ = "TopArtists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    listeners = Column(BigInteger)
    playcount = Column(BigInteger)
    albums = relationship("Album", back_populates="artist")

class Album(Base):
    __tablename__ = "TopAlbums"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    playcount = Column(BigInteger)
    artist_id = Column(Integer, ForeignKey("TopArtists.id"))
    artist = relationship("Artist", back_populates="albums")

SERVER = os.getenv("DB_SERVER", "DESKTOP-DUBDQD2")
DATABASE = os.getenv("DB_DATABASE", "LastFmDatabase")

# Monta uma string ODBC robusta e a injeta em create_engine via odbc_connect
odbc_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
)
quoted = urllib.parse.quote_plus(odbc_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={quoted}", echo=False)


def ensure_bigint_columns():
    """Tenta alterar colunas existentes para BIGINT (se necessário).

    Ignora erros caso as tabelas/colunas não existam ainda.
    """
    stmts = [
        "ALTER TABLE TopArtists ALTER COLUMN listeners BIGINT NULL",
        "ALTER TABLE TopArtists ALTER COLUMN playcount BIGINT NULL",
        "ALTER TABLE TopAlbums ALTER COLUMN playcount BIGINT NULL",
    ]
    with engine.begin() as conn:
        for s in stmts:
            try:
                conn.execute(text(s))
                print(f"[LOAD] Executado: {s}")
            except Exception as e:
                print(f"[LOAD] Falha ao executar: {s} -> {e}")

    # imprimir tipos finais para confirmação
    try:
        ta = get_column_types('TopArtists')
        tb = get_column_types('TopAlbums')
        print('[LOAD] Tipos TopArtists:', ta)
        print('[LOAD] Tipos TopAlbums:', tb)
    except Exception as e:
        print('[LOAD] Não foi possível ler tipos finais:', e)


def get_column_types(table_name: str):
    """Retorna um dict col_name -> data_type para a tabela informada."""
    q = text(
        "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = :t"
    )
    cols = {}
    with engine.connect() as conn:
        res = conn.execute(q, {'t': table_name})
        for r in res:
            # O driver pode retornar tuplas; usar índices para compatibilidade
            try:
                col = r['COLUMN_NAME']
                dtype = r['DATA_TYPE']
            except Exception:
                col = r[0]
                dtype = r[1]
            cols[col] = dtype
    return cols


def test_connection() -> bool:
    """Tenta conectar ao banco e retorna True se ok, False caso contrário.

    Use isto ao debugar cargas vazias para ver se a conexão falha.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[LOAD] Teste de conexão OK")
        return True
    except Exception as e:
        print(f"[LOAD] Falha ao conectar: {e}", file=sys.stderr)
        return False

def initialize_database():
    """Inicializa o banco de dados (cria tabelas e altera colunas).
    
    Chamado apenas uma vez via Streamlit cache.
    """
    Base.metadata.create_all(engine)
    ensure_bigint_columns()
    return True


def recreate_tables(drop_first: bool = False):
    """Recria as tabelas definidas em `Base`.

    Quando `drop_first=True` executa `DROP TABLE` antes de criar.
    Use com cuidado — é destrutivo.
    """
    if drop_first:
        print('[LOAD] Dropando tabelas existentes (destrutivo)')
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)



if __name__ == "__main__":
    ok = test_connection()
    if not ok:
        print("[LOAD] Verifique as configurações de `SERVER`/`DATABASE` e o driver ODBC.")

def insert(df_artists, df_all_albums):
    Session = sessionmaker(bind=engine)

    # Verificações iniciais
    print(f"[LOAD] Iniciando insert(). Artists shape: {getattr(df_artists, 'shape', None)}, Albums shape: {getattr(df_all_albums, 'shape', None)}")
    if df_artists is None or df_artists.empty:
        print("[LOAD] df_artists está vazio — nada a inserir.")
        return
    if df_all_albums is None or df_all_albums.empty:
        print("[LOAD] df_all_albums está vazio — nada a inserir.")
        return

    # Primeira transação: truncar e inserir artistas
    session = Session()
    try:
        session.execute(text("DELETE FROM TopAlbums"))
        session.execute(text("DELETE FROM TopArtists"))

        artist_map = {}
        for _, row in df_artists.iterrows():
            artist = Artist(
                name=row.get("name"),
                listeners=row.get("listeners"),
                playcount=row.get("playcount")
            )
            session.add(artist)
            session.flush()
            artist_map[row.get("name")] = artist.id

        session.commit()
        print(f"[LOAD] Artistas inseridos: {len(artist_map)}")

    except Exception as e:
        session.rollback()
        print(f"[LOAD] Erro ao inserir artistas, rollback executado: {e}")
        session.close()
        raise
    finally:
        session.close()

    # Segunda transação: inserir álbuns usando artist_map
    session2 = Session()
    try:
        skipped = 0
        skipped_list = []
        for _, row in df_all_albums.iterrows():
            artist_name = row.get("artist_name")
            artist_id = artist_map.get(artist_name)
            if artist_id is None:
                skipped += 1
                skipped_list.append({'album': row.get('name'), 'artist_name': artist_name})
                continue

            album = Album(
                name=row.get("name"),
                playcount=row.get("playcount"),
                artist_id=artist_id
            )
            session2.add(album)

        session2.commit()
        print(f"[LOAD] Álbuns inseridos: {len(df_all_albums) - skipped}, Pulados: {skipped}")
        if skipped_list:
            print("[LOAD] Exemplos de álbuns pulados:", skipped_list[:5])

    except Exception as e:
        session2.rollback()
        print(f"[LOAD] Erro durante inserção de álbuns, rollback executado: {e}")
        raise
    finally:
        session2.close()