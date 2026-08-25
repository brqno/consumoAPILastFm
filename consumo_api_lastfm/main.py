import os
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import pandas as pd
import traceback

try:
    from extract.extractAPI import run_extract, search_artist, search_album
    from load.toSQL import insert, initialize_database
    from transform.toST import (
        get_top_artists,
        get_top_albums,
        get_albums_with_artists,
    )
except ImportError as e:
    st.error(f"❌ Erro ao importar módulos: {e}")
    st.write("Certifique-se de que todas as dependências estão instaladas:")
    st.code("pip install streamlit pandas requests pyodbc")
    st.stop()


@st.cache_resource
def init_db():
    """Inicializa o banco de dados apenas uma vez."""
    return initialize_database()


@st.cache_data
def cached_top_artists(limit: int) -> pd.DataFrame:
    return get_top_artists(limit)


@st.cache_data
def cached_top_albums(limit: int) -> pd.DataFrame:
    return get_top_albums(limit)


@st.cache_data
def cached_albums_with_artists(limit: int) -> pd.DataFrame:
    return get_albums_with_artists(limit)


def main() -> None:
    st.set_page_config(page_title="LastFm Dashboard", layout="wide")
    st.title("LastFm — Dashboards básicos")

    # Inicializa o banco de dados apenas uma vez
    try:
        with st.spinner("Inicializando banco de dados..."):
            init_db()
    except Exception as e:
        st.error(f"❌ Erro ao inicializar o banco de dados: {e}")
        st.write("Verifique a conexão com o banco e os logs do terminal.")
        st.stop()

    st.sidebar.header("Configuração")
    view = st.sidebar.selectbox("Visualização", ["Top Artists", "Top Albums", "Albums with Artists"])
    limit = st.sidebar.slider("Limite", min_value=5, max_value=200, value=20, step=5)
    load_data = st.sidebar.button("Carregar dados no banco")

    if load_data:
        with st.spinner("Extraindo e carregando dados..."):
            df_artists, df_albums = run_extract(limit_artists=limit, limit_albums=3)
            st.write("Artistas extraídos:", len(df_artists))
            st.write("Álbuns extraídos:", len(df_albums))
            try:
                insert(df_artists, df_albums)
                cached_top_artists.clear()
                cached_top_albums.clear()
                cached_albums_with_artists.clear()
                st.success("Dados carregados no banco com sucesso.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Erro ao carregar os dados no banco: {e}")

    try:
        if view == "Top Artists":
            search_artist_term = st.text_input("Buscar artista", "")
            if search_artist_term:
                df = search_artist(search_artist_term, limit)
            else:
                df = cached_top_artists(limit)

            if df.empty:
                st.warning("⚠️ Nenhum dado disponível. Clique em 'Carregar dados no banco' primeiro.")
            else:
                st.subheader(f"Top {len(df)} Artists by listeners")
                st.dataframe(df)
                if not df.empty:
                    st.bar_chart(df.set_index("Nome do artista")["Ouvintes"])

        elif view == "Top Albums":
            search_album_term = st.text_input("Buscar álbum", "")
            if search_album_term:
                df = search_album(search_album_term, limit)
            else:
                df = cached_top_albums(limit)

            if df.empty:
                st.warning("⚠️ Nenhum dado disponível. Clique em 'Carregar dados no banco' primeiro.")
            else:
                st.subheader(f"Top {len(df)} Albums by playcount")
                st.dataframe(df)
                if not df.empty:
                    st.bar_chart(df.set_index("Nome do albúm")["Playcount do Albúm"])

        else:
            df = cached_albums_with_artists(limit)
            if df.empty:
                st.warning("⚠️ Nenhum dado disponível. Clique em 'Carregar dados no banco' primeiro.")
            else:
                st.subheader(f"Albums with Artists (Top {len(df)})")
                st.dataframe(df)
                if not df.empty and "Playcount por ouvinte" in df.columns:
                    st.bar_chart(df.set_index("Nome do albúm")["Playcount por ouvinte"].fillna(0))

    except Exception as e:
        st.error(f"❌ Erro ao carregar os dados: {e}")
        st.write("**Detalhes do erro:**")
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
