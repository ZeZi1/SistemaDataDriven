import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date, time
import random
import os
import hashlib
import plotly.express as px 
from dotenv import load_dotenv

# carrega senhas
load_dotenv()

# config da pagina
st.set_page_config(page_title="Dayanne Coutinho Advocacia", layout="wide")

st.markdown("""
<style>
    html, body, [class*="st-"] { font-size: 16px; }
    h1 { font-size: 2.5em; }
    h2 { font-size: 2em; }
    h3 { font-size: 1.5em; }
    .stButton>button { font-size: 1.1em; }
    .stExpander { border: 1px solid #ff4b4b; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# segurança
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

# banco de dados
def init_db():
    conn = sqlite3.connect('dados_advocacia.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS financeiro (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data DATETIME,
                    tipo TEXT,
                    categoria TEXT,
                    descricao TEXT,
                    valor REAL
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS agenda (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora DATETIME,
                    tipo TEXT,
                    cliente TEXT,
                    descricao TEXT,
                    status TEXT
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    username TEXT PRIMARY KEY,
                    password TEXT,
                    funcao TEXT
                )''')
    
    senha_admin = os.getenv("SENHA_ADMIN") or "admin123"
    senha_adv = os.getenv("SENHA_ADVOGADO") or "user123"

    c.execute('SELECT * FROM usuarios WHERE username = "admin"')
    if not c.fetchone():
        c.execute('INSERT INTO usuarios (username, password, funcao) VALUES (?,?,?)', 
                  ("admin", make_hashes(senha_admin), "admin"))
        c.execute('INSERT INTO usuarios (username, password, funcao) VALUES (?,?,?)', 
                  ("advogado", make_hashes(senha_adv), "advogado"))
        
    conn.commit()
    return conn

# ids
def ajustar_sequencia(conn, tabela):
    c = conn.cursor()
    c.execute(f"SELECT MAX(id) FROM {tabela}")
    max_id = c.fetchone()[0]
    if max_id is None: max_id = 0
    c.execute(f"UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (max_id, tabela))
    conn.commit()

def renumerar_tudo(conn):
    c = conn.cursor()
    # 1. financeiro
    df_fin = pd.read_sql("SELECT data, tipo, categoria, descricao, valor FROM financeiro ORDER BY data, id", conn)
    c.execute("DELETE FROM financeiro")
    c.execute("DELETE FROM sqlite_sequence WHERE name='financeiro'")
    for _, row in df_fin.iterrows():
        c.execute("INSERT INTO financeiro (data, tipo, categoria, descricao, valor) VALUES (?, ?, ?, ?, ?)",
                  (row['data'], row['tipo'], row['categoria'], row['descricao'], row['valor']))
    # 2. agenda
    df_age = pd.read_sql("SELECT data_hora, tipo, cliente, descricao, status FROM agenda ORDER BY data_hora, id", conn)
    c.execute("DELETE FROM agenda")
    c.execute("DELETE FROM sqlite_sequence WHERE name='agenda'")
    for _, row in df_age.iterrows():
        c.execute("INSERT INTO agenda (data_hora, tipo, cliente, descricao, status) VALUES (?, ?, ?, ?, ?)",
                  (row['data_hora'], row['tipo'], row['cliente'], row['descricao'], row['status']))
    conn.commit()

# crud
def adicionar_movimentacao(conn, data, tipo, categoria, descricao, valor):
    c = conn.cursor()
    c.execute("INSERT INTO financeiro (data, tipo, categoria, descricao, valor) VALUES (?, ?, ?, ?, ?)",
              (data, tipo, categoria, descricao, valor))
    conn.commit()

def adicionar_evento(conn, data_hora, tipo, cliente, descricao, status):
    c = conn.cursor()
    c.execute("INSERT INTO agenda (data_hora, tipo, cliente, descricao, status) VALUES (?, ?, ?, ?, ?)",
              (data_hora, tipo, cliente, descricao, status))
    conn.commit()

def excluir_registro(conn, tabela, id_registro):
    c = conn.cursor()
    if tabela in ['financeiro', 'agenda']:
        c.execute(f"DELETE FROM {tabela} WHERE id=?", (id_registro,))
        conn.commit()
        ajustar_sequencia(conn, tabela)

def get_financeiro(conn):
    df = pd.read_sql("SELECT * FROM financeiro ORDER BY id DESC", conn)
    if not df.empty:
        
        df['data'] = pd.to_datetime(df['data'], format='mixed', errors='coerce')
    return df

def get_agenda(conn):
    df = pd.read_sql("SELECT * FROM agenda ORDER BY id ASC", conn)
    if not df.empty:
        
        df['data_hora'] = pd.to_datetime(df['data_hora'], format='mixed', errors='coerce')
    return df

def login_user(conn, username, password):
    c = conn.cursor()
    c.execute('SELECT * FROM usuarios WHERE username = ?', (username,))
    data = c.fetchone()
    if data:
        if check_hashes(password, data[1]):
            return data[2]
    return None

# telas
def tela_login(conn):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: white;'>⚖️ Dayanne Coutinho Advocacia</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True) 

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.container():
            st.markdown("### Login")
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type='password')
            if st.button("Entrar", use_container_width=True):
                funcao = login_user(conn, username, password)
                if funcao:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['funcao'] = funcao
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

def tela_sistema(conn):
    st.sidebar.title(f"Olá, {st.session_state['username'].title()}")
    st.sidebar.caption(f"Perfil: {st.session_state['funcao'].upper()}")
    
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()
    st.sidebar.markdown("---")

    st.sidebar.header("📝 Adicionar Novo")
    tipo_cadastro = st.sidebar.radio("Selecione:", ["Agenda/Prazo", "Financeiro"])

    if tipo_cadastro == "Agenda/Prazo":
        with st.sidebar.form("form_agenda", clear_on_submit=True):
            data_input = st.date_input("Data", date.today())
            hora_input = st.time_input("Hora", time(9, 0))
            tipo = st.selectbox("Tipo", ["Prazo Fatal", "Audiência", "Reunião", "Lembrete"])
            cliente = st.text_input("Cliente")
            desc = st.text_area("Descrição")
            
            if st.form_submit_button("💾 Agendar"):
                data_final = datetime.combine(data_input, hora_input)
                adicionar_evento(conn, data_final, tipo, cliente, desc, 'Pendente')
                st.success("Agendado!")
                st.rerun()

    elif tipo_cadastro == "Financeiro":
        tipo_fin = st.sidebar.selectbox("Tipo de Movimentação", ["Receita", "Despesa"])
        
        if tipo_fin == "Receita":
            lista_categorias = ["Honorários Iniciais", "Honorários Êxito", "Consultoria", "Reembolso"]
        else:
            lista_categorias = ["Aluguel", "Taxas Judiciais", "Material Escritório", "Marketing", "Software/Sistemas", "Pessoal/Salário", "Outros"]
            
        with st.sidebar.form("form_fin", clear_on_submit=True):
            cat = st.selectbox("Categoria", lista_categorias)
            data_mov = st.date_input("Data", date.today())
            hora_mov = st.time_input("Hora", time(9, 0))
            desc = st.text_input("Descrição")
            val = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("💾 Registrar"):
                data_completa = datetime.combine(data_mov, hora_mov)
                adicionar_movimentacao(conn, data_completa, tipo_fin, cat, desc, val)
                st.success("Registrado!")
                st.rerun()

    if st.session_state['funcao'] == 'admin':
        with st.sidebar.expander("⚠️ Admin - Manutenção"):
            if st.button("🔄 Renumerar/Organizar IDs"):
                renumerar_tudo(conn)
                st.success("IDs reorganizados!")
                st.rerun()
            st.markdown("---")
            if st.button("❌ Zerar Banco de Dados"):
                conn.close()
                if os.path.exists("dados_advocacia.db"): os.remove("dados_advocacia.db")
                st.cache_data.clear()
                st.session_state['logged_in'] = False
                st.rerun()

    st.markdown(f"## Painel de Controle - {date.today().strftime('%d/%m/%Y')}")
    df_fin = get_financeiro(conn)
    df_age = get_agenda(conn)

    agora = datetime.now()
    if not df_age.empty:
        df_validas = df_age.dropna(subset=['data_hora'])
        if not df_validas.empty:
            alertas = df_validas[(df_validas['data_hora'] >= agora) & (df_validas['data_hora'] <= agora + timedelta(hours=48))]
            if not alertas.empty:
                st.error(f"🚨 URGENTE: {len(alertas)} compromissos nas próximas 48h!")

    tab1, tab2 = st.tabs(["📅 Agenda", "💰 Financeiro"])

    with tab1:
        if not df_age.empty:
            st.dataframe(df_age, use_container_width=True)
            st.markdown("---")
            with st.expander("🗑️ Gerenciar / Excluir Agendamento"):
                lista_agenda = df_age.apply(lambda x: f"ID: {x['id']} | {x['tipo']} - {x['descricao']}", axis=1)
                item_selecionado = st.selectbox("Selecione:", lista_agenda)
                
                if st.button("Excluir Item da Agenda"):
                    
                    id_excluir = int(item_selecionado.split("ID: ")[1].split(" |")[0])
                    excluir_registro(conn, "agenda", id_excluir)
                    st.success("Removido!")
                    st.rerun()
        else:
            st.info("Agenda vazia.")
#graficos
    with tab2:
        if not df_fin.empty:
            rec = df_fin[df_fin['tipo']=='Receita']['valor'].sum()
            des = df_fin[df_fin['tipo']=='Despesa']['valor'].sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("Receitas", f"R$ {rec:,.2f}")
            col2.metric("Despesas", f"R$ {des:,.2f}")
            col3.metric("Saldo", f"R$ {rec - des:,.2f}")
            
            st.markdown("---")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                df_rec = df_fin[df_fin['tipo'] == 'Receita']
                if not df_rec.empty:
                    fig_rec = px.pie(df_rec, values='valor', names='categoria', hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r)
                    st.plotly_chart(fig_rec, use_container_width=True)
            with col_g2:
                df_des = df_fin[df_fin['tipo'] == 'Despesa']
                if not df_des.empty:
                    fig_des = px.pie(df_des, values='valor', names='categoria', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig_des, use_container_width=True)

            st.markdown("---")
            st.dataframe(df_fin, use_container_width=True)
            st.markdown("---")
            with st.expander("🗑️ Gerenciar / Excluir Movimentação"):
                lista_fin = df_fin.apply(lambda x: f"ID: {x['id']} | {x['tipo']} - R$ {x['valor']:.2f}", axis=1)
                item_fin_selecionado = st.selectbox("Selecione:", lista_fin)
                
                if st.button("Excluir Movimentação"):
                    id_excluir = int(item_fin_selecionado.split("ID: ")[1].split(" |")[0])
                    excluir_registro(conn, "financeiro", id_excluir)
                    st.success("Removido!")
                    st.rerun()
        else:
            st.info("Sem dados financeiros.")

def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''
        st.session_state['funcao'] = ''

    conn = init_db()
    if st.session_state['logged_in']:
        tela_sistema(conn)
    else:
        tela_login(conn)

if __name__ == "__main__":
    main()