import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

import pandas as pd
import pyodbc


def conectar() -> pyodbc.Connection:
    """Cria e retorna uma conexão ODBC com o SQL Server.

    Lê `DB_SERVER` e `DB_DATABASE` do ambiente quando disponíveis,
    caso contrário usa os valores locais padrão.
    """
    SERVER = os.getenv("DB_SERVER", "DESKTOP-DUBDQD2")
    DATABASE = os.getenv("DB_DATABASE", "LastFmDatabase")

    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
    )

    return pyodbc.connect(conn_str, timeout=10)


def _close_conn(conn: Optional[pyodbc.Connection]) -> None:
    try:
        if conn is not None:
            conn.close()
    except Exception:
        pass


def get_top_artists(limit: int = 20) -> pd.DataFrame:
    """Retorna os top artistas por `listeners`.

    Args:
        limit: número de linhas a retornar.
    """
    query = (
        "SELECT name AS [Nome do artista], listeners AS [Ouvintes], playcount AS [Playcount] "
        "FROM TopArtists "
        "ORDER BY listeners DESC "
        "OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
    )

    conn = conectar()
    try:
        df = pd.read_sql_query(query, conn, params=[limit])
    finally:
        _close_conn(conn)

    return df


def get_top_albums(limit: int = 20) -> pd.DataFrame:
    """Retorna os top álbuns por `playcount`.

    Args:
        limit: número de linhas a retornar.
    """
    query = (
        "SELECT A.name AS [Nome do albúm], B.name AS Artista, A.playcount AS [Playcount do Albúm] "
        "FROM TopAlbums AS A "
        "INNER JOIN TopArtists AS B ON A.artist_id = B.id "
        "ORDER BY A.playcount DESC "
        "OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
    )

    conn = conectar()
    try:
        df = pd.read_sql_query(query, conn, params=[limit])
    finally:
        _close_conn(conn)

    return df


def get_albums_with_artists(limit: int = 50) -> pd.DataFrame:
    """Retorna álbuns combinados com informações do artista e uma métrica simples.

    A operação de join é feita no banco para performance;
    a métrica `playcount_per_listener` é calculada em pandas.
    """
    query = (
        "SELECT alb.name AS [Nome do albúm], alb.playcount AS [Playcount do Albúm], "
        "art.id AS [ID do Artista], art.name AS [Nome do Artista], art.listeners AS [Ouvintes do Artista] "
        "FROM TopAlbums alb "
        "INNER JOIN TopArtists art ON alb.artist_id = art.id "
        "ORDER BY alb.playcount DESC "
        "OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
    )

    conn = conectar()
    try:
        df = pd.read_sql_query(query, conn, params=[limit])
    finally:
        _close_conn(conn)

    album_playcount = df["Playcount do Albúm"]
    artist_listeners = df["Ouvintes do Artista"].replace({0: pd.NA})
    df["Playcount por ouvinte"] = album_playcount / artist_listeners

    return df


def get_play_trend(entity: str, entity_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """Retorna série temporal de plays para um artista/álbum se existir uma tabela de eventos.

    Observação: esta função assume que existe uma tabela `Plays` com colunas
    `entity_type` ('artist'|'album'), `entity_id`, `played_at` (datetime) e `count`.
    Caso a sua base use outro esquema, adapte a query.
    """
    query = (
        "SELECT CAST(played_at AS DATE) AS play_date, SUM([count]) AS plays "
        "FROM Plays "
        "WHERE entity_type = ? AND entity_id = ? "
    )

    params = [entity, entity_id]
    if start_date:
        query += " AND played_at >= ?"
        params.append(start_date)
    if end_date:
        query += " AND played_at <= ?"
        params.append(end_date)

    query += " GROUP BY CAST(played_at AS DATE) ORDER BY play_date"

    conn = conectar()
    try:
        df = pd.read_sql_query(query, conn, params=params)
    finally:
        _close_conn(conn)

    return df


if __name__ == "__main__":
    # Test rápido local (executa apenas se rodar o módulo diretamente)
    print(get_top_artists(5))

