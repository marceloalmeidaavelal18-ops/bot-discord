import os
import json
import discord
import datetime as dt
import asyncio
from discord.ext import commands, tasks
from discord import app_commands
from typing import Dict, List, Tuple, Optional, Any, Set

# --- Configurações ---
# --- Configurações ---
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ DISCORD_TOKEN não encontrado!")
    print("💡 Configure a variável DISCORD_TOKEN no Railway")
    exit(1)

# --- SERVIDORES PERMITIDOS ---
ALLOWED_SERVERS = [
    1398254768052502639,  # Servidor original (funciona)
    1364716267495227493   # NOVO servidor (a adicionar)
]

# --- CONFIGURAÇÕES POR SERVIDOR ---
def get_server_config(guild_id: int):
    """Retorna as configurações específicas para cada servidor"""
    configs = {
        1398254768052502639: {  # Servidor original
            "CATEGORIA_ID": 1398408627223658536,
            "CATEGORIA_ID_HORAS": 1398408627223658536,
            "CATEGORIA_ARQUIVADOS_ID": 1398408682022113312,
            "CANAL_LEADERBOARD_SEMANAL": 1398260746684596364,
            "CANAL_LEADERBOARD_MENSAL": 1398260674416742546,
            "CARGO_CONSULTA_ID": 1420037335042625678,
            "HORAS_ARQUIVO": "horas_trabalho.json",
            "CONFIG_FILE": "configuracoes_bot.json"
        },
        1364716267495227493: {  # Novo servidor
            "CATEGORIA_ID": 1364716274147524716,
            "CATEGORIA_ID_HORAS": 1364716274147524716,
            "CATEGORIA_ARQUIVADOS_ID": 1367668000676909150,
            "CANAL_LEADERBOARD_SEMANAL": 1420535452070318112,
            "CANAL_LEADERBOARD_MENSAL": 1420535479501062174,
            "CARGO_CONSULTA_ID": 1364716267495227494,
            "HORAS_ARQUIVO": "horas_trabalho_novo.json",
            "CONFIG_FILE": "configuracoes_bot_novo.json"
        }
    }
    
    return configs.get(guild_id, configs[1398254768052502639])

# Variáveis globais (serão sobrescritas por servidor)
CATEGORIA_ID = 1398408627223658536
CATEGORIA_ID_HORAS = 1398408627223658536
CATEGORIA_ARQUIVADOS_ID = 1398408682022113312
CANAL_LEADERBOARD_SEMANAL = 1398260746684596364
CANAL_LEADERBOARD_MENSAL = 1398260674416742546
HORAS_ARQUIVO = "horas_trabalho.json" 
CONFIG_FILE = "configuracoes_bot.json"
BACKUP_DIR = "backups"

NYOX_BOT_NAMES = ["Nyox Bate-Ponto", "Nyox Store", "NYOX", "Bate-Ponto"]
CARGO_CONSULTA_ID = [1420037335042625678, 1364716267495227494]

# --- DECORATOR PARA VERIFICAÇÃO DE SERVIDOR ---
def verificar_servidor_permitido():
    """Decorator para verificar se o comando está sendo usado em servidor permitido"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild.id not in ALLOWED_SERVERS:
            await interaction.response.send_message(
                "❌ Este comando não está disponível neste servidor.",
                ephemeral=True
            )
            return False
        
        # Carregar configurações específicas do servidor
        server_config = get_server_config(interaction.guild.id)
        globals().update(server_config)
        
        return True
    return app_commands.check(predicate)

# --- Funções utilitárias ---
def carregar_horas(guild_id: int = None) -> Dict[str, Any]:
    """Carrega os dados de horas do arquivo JSON específico do servidor"""
    try:
        # Determinar qual arquivo usar baseado no servidor
        if guild_id:
            server_config = get_server_config(guild_id)
            arquivo_horas = server_config["HORAS_ARQUIVO"]
        else:
            # Fallback para o arquivo global (usado apenas quando não há contexto de servidor)
            arquivo_horas = HORAS_ARQUIVO
        
        if not os.path.exists(arquivo_horas):
            print(f"📁 Arquivo {arquivo_horas} não existe, criando...")
            dados_iniciais = {"usuarios": {}, "registros": []}
            with open(arquivo_horas, "w", encoding="utf-8") as f:
                json.dump(dados_iniciais, f, indent=4, ensure_ascii=False)
            return dados_iniciais
        
        with open(arquivo_horas, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados
            
    except Exception as e:
        print(f"❌ Erro ao carregar horas do arquivo {arquivo_horas}: {e}")
        return {"usuarios": {}, "registros": []}

def salvar_horas(dados: Dict[str, Any], guild_id: int = None) -> bool:
    """Salva os dados de horas no arquivo JSON específico do servidor"""
    try:
        # Determinar qual arquivo usar baseado no servidor
        if guild_id:
            server_config = get_server_config(guild_id)
            arquivo_horas = server_config["HORAS_ARQUIVO"]
        else:
            arquivo_horas = HORAS_ARQUIVO
        
        # Fazer backup antes de salvar
        if os.path.exists(arquivo_horas):
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR, exist_ok=True)
            backup_name = f"horas_backup_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = os.path.join(BACKUP_DIR, backup_name)
            try:
                with open(backup_path, "w", encoding="utf-8") as f:
                    json.dump(carregar_horas(guild_id), f, indent=4, ensure_ascii=False)
            except Exception:
                pass
        
        # Salvar dados
        with open(arquivo_horas, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        
        print(f"💾 Dados salvos em {arquivo_horas}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar horas no arquivo {arquivo_horas}: {e}")
        return False

def carregar_configuracoes(guild_id: int = None) -> Dict[str, Any]:
    """Carrega as configurações do bot específicas do servidor"""
    # Determinar qual arquivo de configuração usar
    if guild_id:
        server_config = get_server_config(guild_id)
        config_file = server_config["CONFIG_FILE"]
    else:
        config_file = CONFIG_FILE
    
    config_padrao = {
        "admin_users": [],
        "auto_update": {"ativo": True, "intervalo_minutos": 5, "ultima_atualizacao": None},
        "leaderboard_update": {"ativo": True, "intervalo_horas": 1, "ultima_atualizacao": None},
        "log_channel": None
    }
    
    try:
        if not os.path.exists(config_file):
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_padrao, f, indent=4, ensure_ascii=False)
            return config_padrao
        
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Garantir que todas as chaves existam
            for key, value in config_padrao.items():
                if key not in config:
                    config[key] = value
            return config
    except Exception as e:
        print(f"❌ Erro ao carregar configurações de {config_file}: {e}")
        return config_padrao

def salvar_configuracoes(config: Dict[str, Any], guild_id: int = None) -> bool:
    """Salva as configurações do bot específicas do servidor"""
    try:
        # Determinar qual arquivo de configuração usar
        if guild_id:
            server_config = get_server_config(guild_id)
            config_file = server_config["CONFIG_FILE"]
        else:
            config_file = CONFIG_FILE
            
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar configurações em {config_file}: {e}")
        return False

def normalizar_nome_usuario(nome: str) -> str:
    """Normaliza o nome do usuário"""
    nome = nome.replace('<', '').replace('>', '').replace('@', '').strip()
    
    if nome.isdigit() and len(nome) > 10:
        return f"<@{nome}>"
    
    return nome

def formatar_horas(horas: float) -> str:
    """Formata horas para exibição no formato decimal"""
    return f"{horas:.1f}h"

def obter_periodo_semanal() -> Tuple[dt.date, dt.date]:
    """Retorna o período da semana atual (segunda a domingo)"""
    hoje = dt.date.today()
    segunda_feira = hoje - dt.timedelta(days=hoje.weekday())
    domingo = segunda_feira + dt.timedelta(days=6)
    return segunda_feira, domingo

def obter_periodo_mensal() -> Tuple[dt.date, dt.date]:
    """Retorna o período do mês atual (primeiro ao último dia)"""
    hoje = dt.date.today()
    primeiro_dia = hoje.replace(day=1)
    if hoje.month == 12:
        ultimo_dia = hoje.replace(day=31)
    else:
        ultimo_dia = hoje.replace(month=hoje.month + 1, day=1) - dt.timedelta(days=1)
    return primeiro_dia, ultimo_dia

def agrupar_horas_por_periodo(dados: Dict[str, Any], data_inicio: dt.date, data_fim: dt.date) -> List[Tuple[str, float]]:
    """Agrupa horas por usuário dentro de um período específico"""
    horas_consolidadas = {}
    
    for registro in dados.get("registros", []):
        try:
            data_registro = dt.datetime.strptime(registro["data"], "%Y-%m-%d").date()
            if data_inicio <= data_registro <= data_fim:
                nome_usuario = normalizar_nome_usuario(registro["nome"])
                horas_consolidadas[nome_usuario] = horas_consolidadas.get(nome_usuario, 0.0) + registro["horas"]
        except Exception:
            continue
    
    ranking = [(nome, horas) for nome, horas in horas_consolidadas.items() if horas > 0]
    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking

def agrupar_horas_por_usuario(dados: Dict[str, Any], dias: int = 30) -> List[Tuple[str, float]]:
    """Agrupa todas as horas por usuário"""
    data_limite = (dt.datetime.now() - dt.timedelta(days=dias)).date()
    
    horas_consolidadas = {}
    
    for registro in dados.get("registros", []):
        data_registro = dt.datetime.strptime(registro["data"], "%Y-%m-%d").date()
        if data_registro >= data_limite:
            nome_usuario = normalizar_nome_usuario(registro["nome"])
            if nome_usuario not in horas_consolidadas:
                horas_consolidadas[nome_usuario] = 0.0
            horas_consolidadas[nome_usuario] += registro["horas"]
    
    ranking = [(nome, horas) for nome, horas in horas_consolidadas.items() if horas > 0]
    ranking.sort(key=lambda x: x[1], reverse=True)
    
    return ranking

def obter_nome_amigavel(nome: str, guild: discord.Guild = None) -> str:
    """Tenta obter um nome amigável para o usuário"""
    if nome.startswith('<@') and nome.endswith('>') and nome[2:-1].isdigit():
        user_id = int(nome[2:-1])
        if guild:
            member = guild.get_member(user_id)
            if member:
                return member.display_name
        return f"Usuário {user_id}"
    
    if nome.isdigit() and len(nome) > 10:
        user_id = int(nome)
        if guild:
            member = guild.get_member(user_id)
            if member:
                return member.display_name
        return f"Usuário {user_id}"
    
    return nome

def calcular_total_horas_usuario(dados: Dict[str, Any], usuario_identificador: str, dias: int = None) -> float:
    """Calcula o total de horas de um usuário"""
    total = 0.0
    identificadores = [usuario_identificador]
    
    if usuario_identificador.startswith('<@') and usuario_identificador.endswith('>'):
        user_id = usuario_identificador[2:-1]
        identificadores.extend([user_id, f"@{user_id}"])
    elif usuario_identificador.isdigit():
        identificadores.extend([f"<@{usuario_identificador}>", f"@{usuario_identificador}"])
    
    for registro in dados.get("registros", []):
        if registro["nome"] in identificadores:
            if dias is not None:
                data_registro = dt.datetime.strptime(registro["data"], "%Y-%m-%d").date()
                data_limite = (dt.datetime.now() - dt.timedelta(days=dias)).date()
                if data_registro >= data_limite:
                    total += registro["horas"]
            else:
                total += registro["horas"]
    
    return total

async def verificar_permissao(interaction: discord.Interaction, tipo_comando: str = "consulta") -> bool:
    """Verifica se o usuário tem permissão para usar o comando"""
    config = carregar_configuracoes(interaction.guild.id)  # CORREÇÃO: Passar guild_id
    
    # Administradores do servidor sempre têm permissão total
    if interaction.user.guild_permissions.administrator:
        return True
    
    # Usuários admin definidos nas configurações têm permissão total
    if interaction.user.id in config["admin_users"]:
        return True
    
    # Verificar se o usuário tem o cargo "Oficina Mecânica"
    user_roles = {role.id for role in interaction.user.roles}
    
    # CORREÇÃO: Verificar o cargo específico do servidor
    server_config = get_server_config(interaction.guild.id)
    cargo_consulta_id = server_config["CARGO_CONSULTA_ID"]
    
    tem_cargo_consulta = cargo_consulta_id in user_roles
    
    # Para o comando /minhas_horas, verificar também a categoria
    if tipo_comando == "minhas_horas":
        # Verificar se o comando está sendo usado na categoria correta
        categoria_id_horas = server_config["CATEGORIA_ID_HORAS"]
        if (hasattr(interaction.channel, 'category_id') and 
            interaction.channel.category_id == categoria_id_horas):
            return tem_cargo_consulta
        else:
            return False
    else:
        # Para outros comandos: apenas admin_users e administradores do servidor
        return False

async def criar_embed_leaderboard(dados: Dict[str, Any], dias: int, interaction: discord.Interaction) -> discord.Embed:
    """Cria o embed do leaderboard no estilo original"""
    ranking = agrupar_horas_por_usuario(dados, dias)
    
    if not ranking:
        embed = discord.Embed(
            title="🏆 Ranking de Horas",
            description=f"⚠️ Nenhum registro encontrado nos últimos {dias} dias.",
            color=discord.Color.orange()
        )
        return embed

    total_horas = sum(horas for _, horas in ranking)
    total_participantes = len(ranking)
    
    data_fim = dt.datetime.now().date()
    data_inicio = data_fim - dt.timedelta(days=dias-1)
    
    if dias == 1:
        titulo = "🏆 Ranking do Dia"
    elif dias == 7:
        titulo = "🏆 Ranking da Semana"
    elif dias == 30:
        titulo = "🏆 Ranking do Mês"
    else:
        titulo = f"🏆 Ranking de {dias} Dias"
    
    embed = discord.Embed(
        title=titulo,
        color=discord.Color.gold(),
        timestamp=dt.datetime.now()
    )
    
    embed.add_field(
        name="**Período**",
        value=f"{data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}",
        inline=False
    )
    
    embed.add_field(
        name="**Totais**",
        value=f"**Total de Horas:** {total_horas:.1f}h\n**Total de Participantes:** {total_participantes}",
        inline=False
    )
    
    texto_ranking = ""
    for i, (nome, horas) in enumerate(ranking[:10], start=1):
        nome_amigavel = obter_nome_amigavel(nome, interaction.guild)
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔸"
        texto_ranking += f"{emoji} **{i}. {nome_amigavel}**\n– {formatar_horas(horas)}\n\n"
    
    embed.add_field(
        name=f"**Ranking Top {min(10, len(ranking))}**",
        value=texto_ranking,
        inline=False
    )
    
    if len(ranking) > 10:
        horas_restantes = sum(horas for _, horas in ranking[10:])
        embed.add_field(
            name="**Demais Participantes**",
            value=f"{len(ranking) - 10} usuários com {formatar_horas(horas_restantes)}",
            inline=False
        )
    
    embed.set_footer(text=f"Período de {dias} dias | Atualizado em")
    
    return embed

async def criar_embed_leaderboard_completo(dados: Dict[str, Any], periodo_tipo: str, interaction: discord.Interaction) -> discord.Embed:
    """Cria o embed do leaderboard no formato completo com Ranking 1 e Ranking 2"""
    if periodo_tipo == "semanal":
        data_inicio, data_fim = obter_periodo_semanal()
        titulo = "Leaderboard de Horários"
        periodo_texto = f"**Período**: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}"
    else:
        data_inicio, data_fim = obter_periodo_mensal()
        titulo = "Leaderboard de Horários"
        periodo_texto = f"**Período**: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}"

    ranking = agrupar_horas_por_periodo(dados, data_inicio, data_fim)
    
    if not ranking:
        embed = discord.Embed(
            title=titulo,
            description=f"{periodo_texto}\n\nNenhum registro encontrado.",
            color=discord.Color.orange()
        )
        return embed

    total_horas = sum(horas for _, horas in ranking)
    total_participantes = len(ranking)
    
    # Formatar total de horas para alinhar casas decimais
    total_horas_str = f"{total_horas:.1f}h"
    
    # Criar descrição no formato desejado
    descricao = f"{periodo_texto}\n\n- **Total de Horas**: {total_horas_str}\n- **Total de Participantes**: {total_participantes}\n\n"
    
    embed = discord.Embed(
        title=titulo,
        description=descricao,
        color=discord.Color.gold()
    )
    
    # Função para formatar horas com alinhamento correto
    def formatar_horas_alinhadas(horas: float) -> str:
        """Formata horas garantindo alinhamento das casas decimais"""
        if horas >= 100.0:
            return f"{horas:.1f}h"
        elif horas >= 10.0:
            return f"{horas:.1f}h "
        else:
            return f"{horas:.1f}h  "
    
    # Ranking 1 (posições 1-20)
    ranking1 = ranking[:20]
    texto_ranking1 = ""
    for i, (nome, horas) in enumerate(ranking1, start=1):
        nome_amigavel = obter_nome_amigavel(nome, interaction.guild)
        horas_formatadas = formatar_horas_alinhadas(horas)
        
        # Adicionar emojis para as primeiras posições
        if i == 1:
            emoji = "🥇 "
        elif i == 2:
            emoji = "🥈 "
        elif i == 3:
            emoji = "🥉 "
        else:
            emoji = ""
            
        texto_ranking1 += f"{i}. {emoji}{nome_amigavel} — {horas_formatadas}\n"
    
    if texto_ranking1:
        embed.add_field(name="Ranking 1", value=texto_ranking1, inline=False)
    
    # Ranking 2 (posições 21-100)
    ranking2 = ranking[20:100]
    texto_ranking2 = ""
    for i, (nome, horas) in enumerate(ranking2, start=21):
        nome_amigavel = obter_nome_amigavel(nome, interaction.guild)
        horas_formatadas = formatar_horas_alinhadas(horas)
        texto_ranking2 += f"{i}. {nome_amigavel} — {horas_formatadas}\n"
    
    if texto_ranking2:
        embed.add_field(name="Ranking 2", value=texto_ranking2, inline=False)
    
    embed.set_footer(text=f"Atualizado em {dt.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    return embed

async def atualizar_leaderboards_automaticamente(guild: discord.Guild):
    """Atualiza automaticamente os canais de leaderboard - VERSÃO COMPLETA CORRIGIDA"""
    try:
        print(f"🏆 Iniciando atualização de leaderboards em {guild.name}...")
        
        # Carregar configurações específicas do servidor
        server_config = get_server_config(guild.id)
        CATEGORIA_ID = server_config["CATEGORIA_ID"]
        
        # Processar dados PRIMEIRO
        print(f"📊 Processando dados ANTES das leaderboards...")
        dados_processados = await bot.processar_categoria(guild, CATEGORIA_ID, limite=100)
        
        if not dados_processados:
            print(f"❌ Falha no processamento de dados para {guild.name}")
            return
        
        # AGUARDAR para garantir que os dados estão salvos
        await asyncio.sleep(2)
        
        # CORREÇÃO: Carregar dados do arquivo específico do servidor
        dados = carregar_horas(guild.id)  # ← CORREÇÃO AQUI
        total_registros = len(dados.get("registros", []))
        print(f"✅ Dados carregados: {total_registros} registros (Arquivo: {server_config['HORAS_ARQUIVO']})")
        
        if total_registros == 0:
            print(f"⚠️ Nenhum registro encontrado. Pulando leaderboards.")
            return
        
        # Obter canais de leaderboard
        CANAL_LEADERBOARD_SEMANAL = server_config["CANAL_LEADERBOARD_SEMANAL"]
        CANAL_LEADERBOARD_MENSAL = server_config["CANAL_LEADERBOARD_MENSAL"]
        
        print(f"📋 Canais configurados: Semanal={CANAL_LEADERBOARD_SEMANAL}, Mensal={CANAL_LEADERBOARD_MENSAL}")

        # Criar interação fake
        class FakeInteraction:
            def __init__(self, guild):
                self.guild = guild
                self.user = guild.me
        
        fake_interaction = FakeInteraction(guild)

        # ATUALIZAR LEADERBOARD SEMANAL
        if CANAL_LEADERBOARD_SEMANAL:
            canal_semanal = guild.get_channel(CANAL_LEADERBOARD_SEMANAL)
            if canal_semanal:
                print(f"📋 Processando canal semanal: #{canal_semanal.name} (ID: {canal_semanal.id})")
                
                # Verificar permissões
                permissões = canal_semanal.permissions_for(guild.me)
                print(f"🔐 Permissões no canal semanal: Enviar={permissões.send_messages}, Ler={permissões.read_messages}, Gerir={permissões.manage_messages}")
                
                if not permissões.send_messages:
                    print(f"❌ Bot sem permissão para enviar mensagens em #{canal_semanal.name}")
                else:
                    # Criar embed semanal
                    try:
                        embed_semanal = await criar_embed_leaderboard_completo(dados, "semanal", fake_interaction)
                        print("✅ Embed semanal criado com sucesso")
                    except Exception as e:
                        print(f"❌ Erro ao criar embed semanal: {e}")
                        embed_semanal = None
                    
                    if embed_semanal:
                        # Limpar mensagens antigas
                        try:
                            deleted_count = 0
                            async for message in canal_semanal.history(limit=10):
                                if message.author == guild.me:
                                    try:
                                        await message.delete()
                                        deleted_count += 1
                                        print(f"🗑️ Mensagem antiga apagada: {message.id}")
                                        await asyncio.sleep(0.5)
                                    except Exception as e:
                                        print(f"⚠️ Erro ao apagar mensagem {message.id}: {e}")
                            if deleted_count > 0:
                                print(f"✅ {deleted_count} mensagens antigas apagadas")
                        except Exception as e:
                            print(f"⚠️ Erro ao limpar mensagens: {e}")

                        # Enviar nova mensagem
                        try:
                            mensagem_enviada = await canal_semanal.send(embed=embed_semanal)
                            print(f"✅ Leaderboard semanal ENVIADA COM SUCESSO! Mensagem ID: {mensagem_enviada.id}")
                        except discord.Forbidden:
                            print(f"❌ ERRO DE PERMISSÃO: Bot não pode enviar mensagens em #{canal_semanal.name}")
                        except discord.HTTPException as e:
                            print(f"❌ ERRO HTTP ao enviar: {e}")
                        except Exception as e:
                            print(f"❌ Erro inesperado ao enviar: {e}")
            else:
                print(f"❌ Canal semanal não encontrado (ID: {CANAL_LEADERBOARD_SEMANAL})")
        else:
            print("❌ ID do canal semanal não configurado")

        # ATUALIZAR LEADERBOARD MENSAL
        if CANAL_LEADERBOARD_MENSAL:
            canal_mensal = guild.get_channel(CANAL_LEADERBOARD_MENSAL)
            if canal_mensal:
                print(f"📋 Processando canal mensal: #{canal_mensal.name} (ID: {canal_mensal.id})")
                
                # Verificar permissões
                permissões = canal_mensal.permissions_for(guild.me)
                print(f"🔐 Permissões no canal mensal: Enviar={permissões.send_messages}")
                
                if not permissões.send_messages:
                    print(f"❌ Bot sem permissão para enviar mensagens em #{canal_mensal.name}")
                else:
                    # Criar embed mensal
                    try:
                        embed_mensal = await criar_embed_leaderboard_completo(dados, "mensal", fake_interaction)
                        print("✅ Embed mensal criado com sucesso")
                    except Exception as e:
                        print(f"❌ Erro ao criar embed mensal: {e}")
                        embed_mensal = None
                    
                    if embed_mensal:
                        # Limpar mensagens antigas
                        try:
                            deleted_count = 0
                            async for message in canal_mensal.history(limit=10):
                                if message.author == guild.me:
                                    try:
                                        await message.delete()
                                        deleted_count += 1
                                        await asyncio.sleep(0.5)
                                    except:
                                        pass
                            if deleted_count > 0:
                                print(f"✅ {deleted_count} mensagens mensais apagadas")
                        except:
                            pass

                        # Enviar nova mensagem
                        try:
                            mensagem_enviada = await canal_mensal.send(embed=embed_mensal)
                            print(f"✅ Leaderboard mensal ENVIADA COM SUCESSO! Mensagem ID: {mensagem_enviada.id}")
                        except Exception as e:
                            print(f"❌ Erro ao enviar leaderboard mensal: {e}")
            else:
                print(f"❌ Canal mensal não encontrado (ID: {CANAL_LEADERBOARD_MENSAL})")
        else:
            print("❌ ID do canal mensal não configurado")
                
        print(f"🎯 Atualização de leaderboards concluída para {guild.name}")
        
    except Exception as e:
        print(f"💥 ERRO CRÍTICO em atualizar_leaderboards_automaticamente: {e}")
        import traceback
        traceback.print_exc()

# --- Classe do bot ---
class ASAE(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.config = carregar_configuracoes()  # Configuração global inicial
        self.servidores_verificados = False
        self.dados_processados = False  # Nova flag para controlar se os dados foram processados

    async def setup_hook(self):
        try:
            await self.tree.sync()
            print("✅ Comandos sincronizados com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao sincronizar comandos: {e}")

    @tasks.loop(minutes=5)
    async def auto_update(self):
        """Tarefa de atualização automática a cada 5 minutos"""
        if not self.servidores_verificados:
            return
        
        try:
            for guild in self.guilds:
                # Verificar se é servidor permitido
                if guild.id not in ALLOWED_SERVERS:
                    continue
                    
                # Carregar configurações específicas do servidor
                server_config = get_server_config(guild.id)
                CATEGORIA_ID = server_config["CATEGORIA_ID"]
                
                print(f"🔄 Processando registros em {guild.name}...")
                dados = await self.processar_categoria(guild, CATEGORIA_ID, limite=100)
                
                if dados:
                    self.dados_processados = True  # Marcar que os dados foram processados
                    
                    # CORREÇÃO: Salvar configuração específica do servidor
                    config_servidor = carregar_configuracoes(guild.id)
                    config_servidor["auto_update"]["ultima_atualizacao"] = dt.datetime.now().isoformat()
                    salvar_configuracoes(config_servidor, guild.id)
                    
                    print(f"✅ Dados processados em {guild.name}")
                    
        except Exception as e:
            print(f"❌ Erro na atualização automática: {e}")

    @tasks.loop(hours=1)
    async def leaderboard_hourly_update(self):
        """Tarefa de atualização horária das leaderboards - VERSÃO MELHORADA"""
        try:
            print("⏰ Leaderboard hourly update iniciado")
        
            for guild in self.guilds:
                if guild.id not in ALLOWED_SERVERS:
                    continue
                
                print(f"🏆 Processando leaderboards para {guild.name}...")
            
                # **AGUARDAR processamento de dados primeiro**
                server_config = get_server_config(guild.id)
                CATEGORIA_ID = server_config["CATEGORIA_ID"]
            
                print(f"🔄 Processando dados antes das leaderboards...")
                dados = await self.processar_categoria(guild, CATEGORIA_ID, limite=100)
            
                if dados:
                    # **AGUARDAR para garantir que os dados estão salvos**
                    await asyncio.sleep(3)
                    print(f"✅ Dados processados, iniciando leaderboards...")
                    await atualizar_leaderboards_automaticamente(guild)
                    
                    # CORREÇÃO: Salvar configuração específica do servidor
                    config_servidor = carregar_configuracoes(guild.id)
                    config_servidor["leaderboard_update"]["ultima_atualizacao"] = dt.datetime.now().isoformat()
                    salvar_configuracoes(config_servidor, guild.id)
                else:
                    print(f"❌ Não foi possível processar dados para {guild.name}")
                
            print("✅ Leaderboard hourly update concluído")
            
        except Exception as e:
            print(f"❌ Erro na atualização horária das leaderboards: {e}")

    @auto_update.before_loop
    async def before_auto_update(self):
        await self.wait_until_ready()
        # Aguardar um pouco mais para garantir que tudo está carregado
        await asyncio.sleep(5)

    @leaderboard_hourly_update.before_loop
    async def before_leaderboard_hourly_update(self):
        await self.wait_until_ready()
        # Aguardar o primeiro processamento de dados
        while not self.dados_processados:
            print("⏳ Leaderboard update aguardando processamento inicial...")
            await asyncio.sleep(30)  # Aguardar 30 segundos e verificar novamente
        
        print("⏰ Leaderboard hourly update iniciado - executando a cada 1 hora")

    async def processar_categoria(self, guild: discord.Guild, categoria_id: int, limite: int = 1000) -> Dict[str, Any]:
        """Processa mensagens na categoria especificada"""
        # Verificar se é um servidor permitido
        if guild.id not in ALLOWED_SERVERS:
            print(f"❌ Servidor {guild.name} ({guild.id}) não permitido")
            return carregar_horas(guild.id)  # ← CORREÇÃO AQUI
        
        # Carregar configurações específicas do servidor
        server_config = get_server_config(guild.id)
    
        # Usar o arquivo específico do servidor
        dados = carregar_horas(guild.id)  # ← CORREÇÃO AQUI
        categoria = guild.get_channel(categoria_id)
    
        if not categoria or not isinstance(categoria, discord.CategoryChannel):
            return dados

        registros_processados = 0
        mensagens_processadas = set()
    
        for canal in categoria.channels:
            if not isinstance(canal, discord.TextChannel):
                continue
            
            try:
                async for msg in canal.history(limit=limite):
                    if msg.id in mensagens_processadas:
                        continue
                    mensagens_processadas.add(msg.id)
                
                    if (msg.author.bot and 
                        any(nome in msg.author.display_name for nome in NYOX_BOT_NAMES)):
                    
                        nome_usuario, tempo_horas = self.extrair_info_embed(msg)
                        if nome_usuario and tempo_horas is not None and tempo_horas > 0:
                            hoje = msg.created_at.date().strftime("%Y-%m-%d")
                        
                            registro_existente = None
                            for registro in dados.get("registros", []):
                                if (registro["data"] == hoje and 
                                    registro["nome"] == nome_usuario and
                                    registro.get("mensagem_id") == msg.id):
                                    registro_existente = registro
                                    break
                        
                            if not registro_existente:
                                dados.setdefault("registros", []).append({
                                    "data": hoje,
                                    "nome": nome_usuario,
                                    "horas": tempo_horas,
                                    "mensagem_id": msg.id,
                                    "processado_em": dt.datetime.now().isoformat(),
                                    "servidor_id": guild.id,  # ← ADICIONAR ID DO SERVIDOR
                                    "servidor_nome": guild.name
                                })
                                registros_processados += 1
                            
            except discord.Forbidden:
                continue
            except Exception as e:
                continue

        if registros_processados > 0:
            salvar_horas(dados, guild.id)  # ← CORREÇÃO AQUI
            print(f"📊 Processados {registros_processados} novos registros em {guild.name} (Arquivo: {server_config['HORAS_ARQUIVO']})")
        
        return dados

    def extrair_info_embed(self, msg: discord.Message) -> Tuple[Optional[str], Optional[float]]:
        """Extrai usuário e tempo de mensagens do Nyox"""
        if not msg.embeds:
            return None, None

        for embed in msg.embeds:
            nome_usuario = None
            tempo_horas = 0.0
            
            for field in embed.fields:
                field_name = field.name.lower()
                field_value = field.value.strip()
                
                if "usuário" in field_name or "user" in field_name:
                    nome_usuario = normalizar_nome_usuario(field_value)
                elif "tempo" in field_name or "time" in field_name:
                    texto = field_value.lower()
                    horas = 0
                    minutos = 0
                    
                    if "h" in texto:
                        partes = texto.split("h")
                        try:
                            horas = int(partes[0].strip())
                        except (ValueError, IndexError):
                            pass
                        texto = partes[1] if len(partes) > 1 else ""
                    
                    if "m" in texto:
                        try:
                            minutos = int(texto.split("m")[0].strip())
                        except (ValueError, IndexError):
                            pass
                    
                    tempo_horas = horas + minutos / 60.0
            
            if nome_usuario and tempo_horas > 0:
                return nome_usuario, tempo_horas
        
        return None, None

# --- Instância do bot ---
bot = ASAE()

# --- Middleware de permissões ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    """Middleware para tratar erros de permissão"""
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True
        )
    else:
        print(f"Erro no comando: {error}")

# --- COMANDOS DE CONFIGURAÇÃO ---
@bot.tree.command(name="admin", description="Define administradores do bot")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(acao="Adicionar ou remover administrador", usuario="Usuário para configurar")
@verificar_servidor_permitido()
async def admin(interaction: discord.Interaction, acao: str, usuario: discord.Member):
    """Define administradores do bot"""
    config = carregar_configuracoes(interaction.guild.id)  # CORREÇÃO: Passar guild_id
    
    if acao.lower() == "adicionar":
        if usuario.id not in config["admin_users"]:
            config["admin_users"].append(usuario.id)
            salvar_configuracoes(config, interaction.guild.id)  # CORREÇÃO: Passar guild_id
            embed = discord.Embed(
                title="✅ Administrador Adicionado",
                description=f"{usuario.mention} agora é administrador do bot.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="⚠️ Usuário Já é Administrador",
                description=f"{usuario.mention} já está na lista de administradores.",
                color=discord.Color.orange()
            )
    
    elif acao.lower() == "remover":
        if usuario.id in config["admin_users"]:
            config["admin_users"].remove(usuario.id)
            salvar_configuracoes(config, interaction.guild.id)  # CORREÇÃO: Passar guild_id
            embed = discord.Embed(
                title="✅ Administrador Removido",
                description=f"{usuario.mention} foi removido dos administradores do bot.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Usuário Não é Administrador",
                description=f"{usuario.mention} não está na lista de administradores.",
                color=discord.Color.red()
            )
    
    else:
        embed = discord.Embed(
            title="❌ Ação Inválida",
            description="Use 'adicionar' ou 'remover' como ação.",
            color=discord.Color.red()
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="configuracoes", description="Configura permissões e comportamentos do bot")
@app_commands.checks.has_permissions(administrator=True)
@verificar_servidor_permitido()
async def configuracoes(interaction: discord.Interaction):
    """Menu de configurações do bot"""
    config = carregar_configuracoes(interaction.guild.id)  # CORREÇÃO: Passar guild_id
    
    embed = discord.Embed(
        title="⚙️ Configurações do Bot",
        color=discord.Color.blue(),
        timestamp=dt.datetime.now()
    )
    
    # Informações de administradores
    admin_mentions = []
    for user_id in config["admin_users"]:
        user = interaction.guild.get_member(user_id)
        if user:
            admin_mentions.append(user.mention)
        else:
            admin_mentions.append(f"`{user_id}`")
    
    embed.add_field(
        name="👑 Administradores",
        value="\n".join(admin_mentions) if admin_mentions else "Nenhum administrador definido",
        inline=False
    )
    
    # Informação do cargo de consulta (específico do servidor)
    server_config = get_server_config(interaction.guild.id)
    cargo_consulta_id = server_config["CARGO_CONSULTA_ID"]
    cargo_consulta = interaction.guild.get_role(cargo_consulta_id)
    
    if cargo_consulta:
        embed.add_field(
            name="👥 Cargo de Consulta",
            value=f"{cargo_consulta.mention}\n*Acesso apenas ao comando /minhas_horas*",
            inline=False
        )
    
    # Configuração de auto-update
    status_auto = "✅ Ativo" if config["auto_update"]["ativo"] else "❌ Inativo"
    intervalo = config["auto_update"]["intervalo_minutos"]
    embed.add_field(
        name="🔄 Auto-Update Pontos",
        value=f"Status: {status_auto}\nIntervalo: {intervalo} minutos",
        inline=False
    )
    
    # Configuração de leaderboard update
    status_leaderboard = "✅ Ativo" if config["leaderboard_update"]["ativo"] else "❌ Inativo"
    intervalo_horas = config["leaderboard_update"].get("intervalo_horas", 1)
    embed.add_field(
        name="🏆 Auto-Update Leaderboards",
        value=f"Status: {status_leaderboard}\nIntervalo: {intervalo_horas} hora(s)",
        inline=False
    )
    
    # Canal de log
    if config["log_channel"]:
        channel = interaction.guild.get_channel(config["log_channel"])
        canal_info = channel.mention if channel else f"`{config['log_channel']}` (não encontrado)"
    else:
        canal_info = "Não definido"
    
    embed.add_field(name="📋 Canal de Log", value=canal_info, inline=True)
    
    # Informações do arquivo usado
    arquivo_horas = server_config["HORAS_ARQUIVO"]
    arquivo_config = server_config["CONFIG_FILE"]
    embed.add_field(
        name="📁 Arquivos do Servidor",
        value=f"Horas: `{arquivo_horas}`\nConfig: `{arquivo_config}`",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="config_auto_update", description="Configura atualização automática")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(status="Ativar ou desativar auto-update", intervalo_minutos="Intervalo em minutos (padrão: 5)")
@verificar_servidor_permitido()
async def config_auto_update(interaction: discord.Interaction, status: bool, intervalo_minutos: int = 5):
    """Configura a atualização automática"""
    if intervalo_minutos < 1:
        await interaction.response.send_message("❌ Intervalo deve ser pelo menos 1 minuto.", ephemeral=True)
        return
    
    config = carregar_configuracoes(interaction.guild.id)  # CORREÇÃO: Passar guild_id
    config["auto_update"]["ativo"] = status
    config["auto_update"]["intervalo_minutos"] = intervalo_minutos
    
    if salvar_configuracoes(config, interaction.guild.id):  # CORREÇÃO: Passar guild_id
        # Atualizar a tarefa
        bot.auto_update.change_interval(minutes=intervalo_minutos)
        
        status_text = "✅ Ativado" if status else "❌ Desativado"
        embed = discord.Embed(
            title="🔄 Auto-Update Configurado",
            color=discord.Color.green(),
            description=f"Status: {status_text}\nIntervalo: {intervalo_minutos} minutos"
        )
        
        if status:
            bot.auto_update.restart()
        else:
            bot.auto_update.cancel()
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("❌ Erro ao salvar configurações.", ephemeral=True)

@bot.tree.command(name="config_leaderboard_update", description="Configura atualização automática das leaderboards")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(status="Ativar ou desativar auto-update das leaderboards", intervalo_horas="Intervalo em horas (padrão: 1)")
@verificar_servidor_permitido()
async def config_leaderboard_update(interaction: discord.Interaction, status: bool, intervalo_horas: int = 1):
    """Configura a atualização automática das leaderboards"""
    if intervalo_horas < 1:
        await interaction.response.send_message("❌ Intervalo deve ser pelo menos 1 hora.", ephemeral=True)
        return
    
    config = carregar_configuracoes(interaction.guild.id)  # CORREÇÃO: Passar guild_id
    config["leaderboard_update"]["ativo"] = status
    config["leaderboard_update"]["intervalo_horas"] = intervalo_horas
    
    if salvar_configuracoes(config, interaction.guild.id):  # CORREÇÃO: Passar guild_id
        # Atualizar a tarefa
        bot.leaderboard_hourly_update.change_interval(hours=intervalo_horas)
        
        status_text = "✅ Ativado" if status else "❌ Desativado"
        embed = discord.Embed(
            title="🏆 Auto-Update Leaderboards Configurado",
            color=discord.Color.green(),
            description=f"Status: {status_text}\nIntervalo: {intervalo_horas} hora(s)"
        )
        
        if status:
            bot.leaderboard_hourly_update.restart()
        else:
            bot.leaderboard_hourly_update.cancel()
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("❌ Erro ao salvar configurações.", ephemeral=True)

@bot.tree.command(name="config_log_channel", description="Define o canal para logs do bot")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(canal="Canal para enviar logs")
@verificar_servidor_permitido()
async def config_log_channel(interaction: discord.Interaction, canal: discord.TextChannel):
    """Define o canal de log"""
    config = carregar_configuracoes(interaction.guild.id)  # CORREÇÃO: Passar guild_id
    config["log_channel"] = canal.id
    
    if salvar_configuracoes(config, interaction.guild.id):  # CORREÇÃO: Passar guild_id
        embed = discord.Embed(
            title="✅ Canal de Log Definido",
            description=f"Logs serão enviados para {canal.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("❌ Erro ao salvar configurações.", ephemeral=True)

# --- COMANDOS PRINCIPAIS ---
@bot.tree.command(name="atualizar", description="Lê pontos do Nyox e atualiza registros")
@verificar_servidor_permitido()
async def atualizar(interaction: discord.Interaction):
    """Atualiza os registros de horas"""
    if not await verificar_permissao(interaction, "admin"):
        await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Carregar configurações específicas do servidor
        server_config = get_server_config(interaction.guild.id)
        CATEGORIA_ID = server_config["CATEGORIA_ID"]
        
        dados = await bot.processar_categoria(interaction.guild, CATEGORIA_ID)
        total_registros = len(dados.get("registros", []))
        
        ranking = agrupar_horas_por_usuario(dados, dias=365)
        usuarios_unicos = len(ranking)
        
        embed = discord.Embed(
            title="✅ Atualização Concluída",
            color=discord.Color.green(),
            timestamp=dt.datetime.now()
        )
        embed.add_field(name="Usuários únicos", value=usuarios_unicos, inline=True)
        embed.add_field(name="Total de registros", value=total_registros, inline=True)
        embed.add_field(name="Arquivo usado", value=server_config["HORAS_ARQUIVO"], inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Erro na Atualização",
            description=f"Ocorreu um erro: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="atualizar_leaderboards", description="Força a atualização das leaderboards automáticas")
@verificar_servidor_permitido()
async def atualizar_leaderboards(interaction: discord.Interaction):
    """Atualiza as leaderboards nos canais designados"""
    if not await verificar_permissao(interaction, "admin"):
        await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        await atualizar_leaderboards_automaticamente(interaction.guild)
        embed = discord.Embed(
            title="✅ Leaderboards Atualizadas",
            description="As leaderboards foram atualizadas nos canais designados.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Erro ao Atualizar Leaderboards",
            description=f"Ocorreu um erro: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="adicionar_horas", description="Adiciona horas a um usuário")
@app_commands.describe(usuario="Usuário para adicionar horas", horas="Quantidade de horas a adicionar", data="Data no formato YYYY-MM-DD (opcional)")
@verificar_servidor_permitido()
async def adicionar_horas(interaction: discord.Interaction, usuario: str, horas: float, data: str = None):
    """Adiciona horas manualmente"""
    if not await verificar_permissao(interaction, "admin"):
        await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        return
    
    if horas <= 0:
        await interaction.response.send_message("❌ As horas devem ser maiores que zero.", ephemeral=True)
        return

    # Validar e formatar data
    if data:
        try:
            dt.datetime.strptime(data, "%Y-%m-%d")
        except ValueError:
            await interaction.response.send_message("❌ Formato de data inválido. Use YYYY-MM-DD.", ephemeral=True)
            return
    else:
        data = dt.datetime.now().date().strftime("%Y-%m-%d")

    # CORREÇÃO: Carregar dados do servidor específico
    dados = carregar_horas(interaction.guild.id)
    
    # Normalizar identificador do usuário
    if usuario.startswith('<@') and usuario.endswith('>'):
        usuario_id = usuario[2:-1]
        try:
            member = await interaction.guild.fetch_member(int(usuario_id))
            nome_usuario = member.display_name
            identificador = usuario
        except:
            nome_usuario = f"Usuário {usuario_id}"
            identificador = usuario
    else:
        if usuario.isdigit() and len(usuario) > 10:
            try:
                member = await interaction.guild.fetch_member(int(usuario))
                nome_usuario = member.display_name
                identificador = f"<@{usuario}>"
            except:
                nome_usuario = f"Usuário {usuario}"
                identificador = usuario
        else:
            nome_usuario = usuario
            identificador = usuario

    # Adicionar registro
    dados.setdefault("registros", []).append({
        "data": data,
        "nome": identificador,
        "horas": horas,
        "adicionado_manual": True,
        "adicionado_por": interaction.user.display_name,
        "adicionado_em": dt.datetime.now().isoformat()
    })

    # CORREÇÃO: Salvar no arquivo específico do servidor
    if salvar_horas(dados, interaction.guild.id):
        total_atual = calcular_total_horas_usuario(dados, identificador)
        
        embed = discord.Embed(
            title="✅ Horas Adicionadas",
            color=discord.Color.green(),
            timestamp=dt.datetime.now()
        )
        embed.add_field(name="Usuário", value=nome_usuario, inline=True)
        embed.add_field(name="Horas Adicionadas", value=formatar_horas(horas), inline=True)
        embed.add_field(name="Data", value=data, inline=True)
        embed.add_field(name="Total Atual", value=formatar_horas(total_atual), inline=True)
        embed.add_field(name="Adicionado por", value=interaction.user.display_name, inline=True)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Erro ao salvar as horas.", ephemeral=True)

@bot.tree.command(name="remover_horas", description="Remove horas de um usuário")
@app_commands.describe(usuario="Usuário para remover horas", horas="Quantidade de horas a remover", data="Data específica (opcional)")
@verificar_servidor_permitido()
async def remover_horas(interaction: discord.Interaction, usuario: str, horas: float, data: str = None):
    """Remove horas de um usuário"""
    if not await verificar_permissao(interaction, "admin"):
        await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        return
    
    if horas <= 0:
        await interaction.response.send_message("❌ As horas devem ser maiores que zero.", ephemeral=True)
        return

    # CORREÇÃO: Carregar dados do servidor específico
    dados = carregar_horas(interaction.guild.id)
    
    # Normalizar identificador do usuário
    if usuario.startswith('<@') and usuario.endswith('>'):
        usuario_id = usuario[2:-1]
        identificador = usuario
    elif usuario.isdigit() and len(usuario) > 10:
        identificador = f"<@{usuario}>"
    else:
        identificador = usuario

    # Calcular total atual antes da remoção
    total_antes = calcular_total_horas_usuario(dados, identificador)
    
    if total_antes == 0:
        await interaction.response.send_message("❌ Este usuário não possui horas registradas.", ephemeral=True)
        return

    # Filtrar registros do usuário
    registros_usuario = []
    outros_registros = []
    
    for registro in dados.get("registros", []):
        if registro["nome"] == identificador:
            if data is None or registro["data"] == data:
                registros_usuario.append(registro)
            else:
                outros_registros.append(registro)
        else:
            outros_registros.append(registro)

    # Ordenar registros por data (mais recente primeiro)
    registros_usuario.sort(key=lambda x: x["data"], reverse=True)
    
    # Remover horas dos registros mais recentes primeiro
    horas_restantes = horas
    registros_modificados = []
    
    for registro in registros_usuario:
        if horas_restantes <= 0:
            outros_registros.append(registro)
            continue
            
        if registro["horas"] > horas_restantes:
            registro["horas"] -= horas_restantes
            registro["modificado_em"] = dt.datetime.now().isoformat()
            registro["modificado_por"] = interaction.user.display_name
            registro["horas_removidas"] = horas_restantes
            outros_registros.append(registro)
            horas_restantes = 0
        else:
            horas_restantes -= registro["horas"]
            registros_modificados.append(registro)

    # Se ainda sobrou horas para remover, mostrar aviso
    if horas_restantes > 0:
        await interaction.response.send_message(
            f"⚠️ Aviso: Foram removidas apenas {formatar_horas(horas - horas_restantes)} "
            f"(de {formatar_horas(horas)} solicitadas).",
            ephemeral=True
        )

    # Atualizar dados
    dados["registros"] = outros_registros
    
    # CORREÇÃO: Salvar no arquivo específico do servidor
    if salvar_horas(dados, interaction.guild.id):
        total_depois = calcular_total_horas_usuario(dados, identificador)
        
        embed = discord.Embed(
            title="✅ Horas Removidas",
            color=discord.Color.orange(),
            timestamp=dt.datetime.now()
        )
        embed.add_field(name="Usuário", value=obter_nome_amigavel(identificador, interaction.guild), inline=True)
        embed.add_field(name="Horas Removidas", value=formatar_horas(min(horas, horas - horas_restantes)), inline=True)
        embed.add_field(name="Total Antes", value=formatar_horas(total_antes), inline=True)
        embed.add_field(name="Total Depois", value=formatar_horas(total_depois), inline=True)
        embed.add_field(name="Removido por", value=interaction.user.display_name, inline=True)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Erro ao salvar as alterações.", ephemeral=True)

@bot.tree.command(name="horas_usuario", description="Mostra as horas trabalhadas de um usuário")
@app_commands.describe(usuario="Usuário para consultar as horas", dias="Número de dias para visualizar (padrão: 30)")
@verificar_servidor_permitido()
async def horas_usuario(interaction: discord.Interaction, usuario: discord.Member, dias: int = 30):
    """Mostra as horas de um usuário específico"""
    if not await verificar_permissao(interaction, "admin"):
        await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        return
    
    # CORREÇÃO: Carregar dados do servidor específico
    dados = carregar_horas(interaction.guild.id)
    
    # Identificadores possíveis para o usuário
    identificadores = [
        usuario.display_name,
        f"<@{usuario.id}>",
        str(usuario.id)
    ]
    
    total_periodo = 0
    registros_usuario = []
    data_limite = (dt.datetime.now() - dt.timedelta(days=dias)).date()
    
    for registro in dados.get("registros", []):
        data_registro = dt.datetime.strptime(registro["data"], "%Y-%m-%d").date()
        
        if data_registro >= data_limite and registro["nome"] in identificadores:
            total_periodo += registro["horas"]
            registros_usuario.append(registro)
    
    if not registros_usuario:
        await interaction.response.send_message(
            f"⚠️ Não foram encontrados registros para {usuario.mention} nos últimos {dias} dias.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"⏰ Horas de {usuario.display_name} ({dias} dias)",
        color=discord.Color.blue(),
        description=f"**Total: {formatar_horas(total_periodo)}**"
    )
    
    # Agrupar por data
    horas_por_data = {}
    for registro in registros_usuario:
        if registro["data"] not in horas_por_data:
            horas_por_data[registro["data"]] = 0
        horas_por_data[registro["data"]] += registro["horas"]
    
    # Ordenar por data (mais recente primeiro)
    datas_ordenadas = sorted(horas_por_data.keys(), reverse=True)
    
    for data in datas_ordenadas[:7]:  # Mostrar até 7 dias
        embed.add_field(
            name=f"📅 {data}",
            value=formatar_horas(horas_por_data[data]),
            inline=False
        )
    
    # Adicionar informações do usuário
    embed.set_thumbnail(url=usuario.display_avatar.url)
    embed.add_field(
        name="👤 Usuário",
        value=f"{usuario.mention}\n{usuario.display_name}",
        inline=True
    )
    
    embed.add_field(
        name="📊 Estatísticas",
        value=f"**Dias com registros:** {len(horas_por_data)}\n**Total de registros:** {len(registros_usuario)}",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="resetar_horas", description="Reseta todas as horas de um usuário")
@app_commands.describe(usuario="Usuário para resetar horas", confirmacao="Digite 'CONFIRMAR' para resetar")
@verificar_servidor_permitido()
async def resetar_horas(interaction: discord.Interaction, usuario: str, confirmacao: str):
    """Reseta todas as horas de um usuário"""
    if not await verificar_permissao(interaction, "admin"):
        await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        return
    
    if confirmacao != "CONFIRMAR":
        await interaction.response.send_message(
            "❌ Confirmação necessária. Digite 'CONFIRMAR' para resetar as horas.",
            ephemeral=True
        )
        return

    # CORREÇÃO: Carregar dados do servidor específico
    dados = carregar_horas(interaction.guild.id)
    
    # Normalizar identificador do usuário
    if usuario.startswith('<@') and usuario.endswith('>'):
        usuario_id = usuario[2:-1]
        identificador = usuario
    elif usuario.isdigit() and len(usuario) > 10:
        identificador = f"<@{usuario}>"
    else:
        identificador = usuario

    # Calcular total antes do reset
    total_antes = calcular_total_horas_usuario(dados, identificador)
    
    if total_antes == 0:
        await interaction.response.send_message("❌ Este usuário não possui horas registradas.", ephemeral=True)
        return

    # Filtrar registros (manter apenas os que NÃO são do usuário)
    registros_antes = len(dados.get("registros", []))
    dados["registros"] = [r for r in dados.get("registros", []) if r["nome"] != identificador]
    registros_depois = len(dados.get("registros", []))
    registros_removidos = registros_antes - registros_depois

    # CORREÇÃO: Salvar no arquivo específico do servidor
    if salvar_horas(dados, interaction.guild.id):
        embed = discord.Embed(
            title="✅ Horas Resetadas",
            color=discord.Color.red(),
            timestamp=dt.datetime.now()
        )
        embed.add_field(name="Usuário", value=obter_nome_amigavel(identificador, interaction.guild), inline=True)
        embed.add_field(name="Total de Horas Removidas", value=formatar_horas(total_antes), inline=True)
        embed.add_field(name="Registros Removidos", value=registros_removidos, inline=True)
        embed.add_field(name="Resetado por", value=interaction.user.display_name, inline=True)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Erro ao salvar as alterações.", ephemeral=True)

@bot.tree.command(name="arquivados", description="Verifica a categoria de arquivados e remove TODAS as horas dos usuários")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(confirmar="Digite 'CONFIRMAR' para realmente remover TODAS as horas")
@verificar_servidor_permitido()
async def arquivados(interaction: discord.Interaction, confirmar: str = None):
    """Verifica a categoria de arquivados e remove TODAS as horas dos usuários"""
    if not await verificar_permissao(interaction, "admin"):
        await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    
    try:
        # Obter a categoria arquivados específica do servidor
        server_config = get_server_config(interaction.guild.id)
        CATEGORIA_ARQUIVADOS_ID = server_config["CATEGORIA_ARQUIVADOS_ID"]
        
        categoria = interaction.guild.get_channel(CATEGORIA_ARQUIVADOS_ID)
        if not categoria:
            await interaction.followup.send("❌ Categoria de arquivados não encontrada.", ephemeral=True)
            return
        
        # Carregar dados do servidor específico
        dados = carregar_horas(interaction.guild.id)
        
        # Verificar se há confirmação
        if confirmar != "CONFIRMAR":
            # PRIMEIRO: Verificar quais canais existem na categoria de arquivados
            canais_arquivados = []
            for canal in categoria.channels:
                if isinstance(canal, discord.TextChannel):
                    canais_arquivados.append(canal)
            
            if not canais_arquivados:
                embed = discord.Embed(
                    title="📂 Categoria de Arquivados",
                    description="Nenhum canal de texto encontrado na categoria de arquivados.",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # SEGUNDO: Identificar usuários pelos NOMES DOS CANAIS
            usuarios_dos_canais = set()
            
            for canal in canais_arquivados:
                # Extrair nome de usuário do nome do canal (ignorar canais de sistema)
                nome_canal = canal.name.lower()
                
                # Ignorar canais que não parecem ser de usuários específicos
                palavras_ignorar = ["arquivado", "archive", "geral", "general", "chat", "categoria", "category"]
                if any(palavra in nome_canal for palavra in palavras_ignorar):
                    continue
                
                # Tentar limpar o nome do canal para extrair o nome do usuário
                nome_limpo = nome_canal.replace("-", " ").replace("_", " ").replace("arquivada", "").replace("archived", "").strip()
                if nome_limpo and len(nome_limpo) > 2:  # Evitar nomes muito curtos
                    usuarios_dos_canais.add(nome_limpo.title())
            
            # TERCEIRO: Verificar mensagens do Nyox dentro dos canais arquivados
            usuarios_das_mensagens = set()
            mensagens_processadas = 0
            
            for canal in canais_arquivados[:10]:  # Limitar a 10 canais para não demorar muito
                try:
                    async for msg in canal.history(limit=50):  # Limitar a 50 mensagens por canal
                        if msg.author.bot and any(nome in msg.author.display_name for nome in NYOX_BOT_NAMES):
                            nome_usuario, _ = bot.extrair_info_embed(msg)
                            if nome_usuario:
                                usuarios_das_mensagens.add(nome_usuario)
                                mensagens_processadas += 1
                except discord.Forbidden:
                    continue
                except Exception as e:
                    print(f"Erro ao ler histórico do canal {canal.name}: {e}")
            
            # COMBINAR ambas as listas
            todos_usuarios_arquivados = usuarios_dos_canais.union(usuarios_das_mensagens)
            
            if not todos_usuarios_arquivados:
                embed = discord.Embed(
                    title="📂 Categoria de Arquivados",
                    description="Nenhum usuário identificado na categoria de arquivados.",
                    color=discord.Color.blue()
                )
                # Mostrar apenas alguns canais para não exceder limite
                nomes_canais = [f"• #{c.name}" for c in canais_arquivados[:10]]
                texto_canais = "\n".join(nomes_canais)
                if len(canais_arquivados) > 10:
                    texto_canais += f"\n... e mais {len(canais_arquivados) - 10} canais"
                
                embed.add_field(
                    name="Canais encontrados",
                    value=texto_canais,
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # QUARTO: Buscar correspondências nos registros de horas
            usuarios_com_horas = []
            total_geral = 0
            
            # Primeiro, criar uma lista de todos os nomes únicos nos registros
            todos_nos_registros = set()
            for registro in dados.get("registros", []):
                nome_amigavel = obter_nome_amigavel(registro["nome"], interaction.guild)
                todos_nos_registros.add((registro["nome"], nome_amigavel))
            
            # Agora tentar fazer matching mais inteligente
            for usuario_arquivado in todos_usuarios_arquivados:
                # Tentar encontrar correspondência
                for nome_registro, nome_amigavel in todos_nos_registros:
                    nome_amigavel_lower = nome_amigavel.lower()
                    usuario_arquivado_lower = usuario_arquivado.lower()
                    
                    # Verificar matching por similaridade (mais tolerante)
                    if (usuario_arquivado_lower in nome_amigavel_lower or 
                        nome_amigavel_lower in usuario_arquivado_lower or
                        usuario_arquivado_lower == nome_amigavel_lower):
                        
                        total_horas = calcular_total_horas_usuario(dados, nome_registro)
                        if total_horas > 0:
                            # Verificar se já não adicionamos este usuário
                            if not any(u[0] == nome_registro for u in usuarios_com_horas):
                                usuarios_com_horas.append((nome_registro, total_horas))
                                total_geral += total_horas
                            break
            
            if not usuarios_com_horas:
                embed = discord.Embed(
                    title="📂 Categoria de Arquivados",
                    description="Usuários encontrados na categoria, mas nenhum tem horas registradas ou não foi possível fazer a correspondência.",
                    color=discord.Color.blue()
                )
                
                # Limitar a exibição de usuários
                usuarios_texto = "\n".join([f"• {u}" for u in list(todos_usuarios_arquivados)[:10]])
                if len(todos_usuarios_arquivados) > 10:
                    usuarios_texto += f"\n... e mais {len(todos_usuarios_arquivados) - 10} usuários"
                
                embed.add_field(
                    name="👥 Usuários identificados na categoria",
                    value=usuarios_texto,
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Ordenar por horas (maior primeiro)
            usuarios_com_horas.sort(key=lambda x: x[1], reverse=True)
            
            embed = discord.Embed(
                title="⚠️ CONFIRMAÇÃO REQUERIDA - Reset de Horas",
                description=f"**Esta ação irá remover TODAS as horas dos usuários identificados na categoria de arquivados.**\n\n"
                          f"**Total de horas a serem removidas:** {formatar_horas(total_geral)}\n"
                          f"**Total de usuários afetados:** {len(usuarios_com_horas)}\n\n"
                          f"**⚠️ ESTA AÇÃO É IRREVERSÍVEL!**\n"
                          f"Para confirmar, use: `/arquivados confirmar: CONFIRMAR`",
                color=discord.Color.red()
            )
            
            # Adicionar lista de usuários (limitada)
            lista_usuarios = ""
            for i, (usuario, horas) in enumerate(usuarios_com_horas[:8], 1):  # Limitar a 8
                nome_amigavel = obter_nome_amigavel(usuario, interaction.guild)
                lista_usuarios += f"{i}. {nome_amigavel} - {formatar_horas(horas)}\n"
            
            if len(usuarios_com_horas) > 8:
                lista_usuarios += f"\n... e mais {len(usuarios_com_horas) - 8} usuários"
            
            embed.add_field(
                name="👥 Usuários que terão horas resetadas",
                value=lista_usuarios or "Nenhum usuário encontrado",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        else:
            # CONFIRMAÇÃO RECEBIDA - EXECUTAR AÇÃO
            # Repetir o processo de identificação para garantir que estamos resetando os mesmos usuários
            canais_arquivados = []
            for canal in categoria.channels:
                if isinstance(canal, discord.TextChannel):
                    canais_arquivados.append(canal)
            
            if not canais_arquivados:
                await interaction.followup.send("❌ Nenhum canal encontrado na categoria de arquivados.", ephemeral=True)
                return
            
            # Identificar usuários (mesma lógica do preview)
            usuarios_dos_canais = set()
            for canal in canais_arquivados:
                nome_canal = canal.name.lower()
                palavras_ignorar = ["arquivado", "archive", "geral", "general", "chat", "categoria", "category"]
                if any(palavra in nome_canal for palavra in palavras_ignorar):
                    continue
                nome_limpo = nome_canal.replace("-", " ").replace("_", " ").replace("arquivada", "").replace("archived", "").strip()
                if nome_limpo and len(nome_limpo) > 2:
                    usuarios_dos_canais.add(nome_limpo.title())
            
            usuarios_das_mensagens = set()
            for canal in canais_arquivados[:10]:
                try:
                    async for msg in canal.history(limit=50):
                        if msg.author.bot and any(nome in msg.author.display_name for nome in NYOX_BOT_NAMES):
                            nome_usuario, _ = bot.extrair_info_embed(msg)
                            if nome_usuario:
                                usuarios_das_mensagens.add(nome_usuario)
                except:
                    continue
            
            todos_usuarios_arquivados = usuarios_dos_canais.union(usuarios_das_mensagens)
            
            if not todos_usuarios_arquivados:
                await interaction.followup.send("❌ Nenhum usuário identificado para reset.", ephemeral=True)
                return
            
            # Encontrar correspondências exatas nos registros
            usuarios_para_resetar = set()
            todos_nos_registros = set()
            for registro in dados.get("registros", []):
                nome_amigavel = obter_nome_amigavel(registro["nome"], interaction.guild)
                todos_nos_registros.add((registro["nome"], nome_amigavel))
            
            for usuario_arquivado in todos_usuarios_arquivados:
                for nome_registro, nome_amigavel in todos_nos_registros:
                    nome_amigavel_lower = nome_amigavel.lower()
                    usuario_arquivado_lower = usuario_arquivado.lower()
                    
                    if (usuario_arquivado_lower in nome_amigavel_lower or 
                        nome_amigavel_lower in usuario_arquivado_lower or
                        usuario_arquivado_lower == nome_amigavel_lower):
                        usuarios_para_resetar.add(nome_registro)
                        break
            
            if not usuarios_para_resetar:
                await interaction.followup.send("❌ Nenhuma correspondência encontrada para reset.", ephemeral=True)
                return
            
            # Resetar horas de cada usuário encontrado
            total_registros_antes = len(dados.get("registros", []))
            horas_removidas_total = 0
            usuarios_afetados = []
            
            for usuario in usuarios_para_resetar:
                total_antes = calcular_total_horas_usuario(dados, usuario)
                if total_antes > 0:
                    # Remover todos os registros deste usuário
                    dados["registros"] = [r for r in dados.get("registros", []) if r["nome"] != usuario]
                    horas_removidas_total += total_antes
                    usuarios_afetados.append((usuario, total_antes))
            
            total_registros_depois = len(dados.get("registros", []))
            registros_removidos = total_registros_antes - total_registros_depois
            
            # Salvar as alterações
            if salvar_horas(dados, interaction.guild.id):
                embed = discord.Embed(
                    title="✅ Horas Resetadas com Sucesso",
                    description=f"**Total de horas removidas:** {formatar_horas(horas_removidas_total)}\n"
                              f"**Registros removidos:** {registros_removidos}\n"
                              f"**Usuários afetados:** {len(usuarios_afetados)}",
                    color=discord.Color.green()
                )
                
                # Adicionar lista de usuários resetados (limitada)
                if usuarios_afetados:
                    lista_usuarios = ""
                    for i, (usuario, horas) in enumerate(usuarios_afetados[:5], 1):
                        nome_amigavel = obter_nome_amigavel(usuario, interaction.guild)
                        lista_usuarios += f"{i}. {nome_amigavel} - {formatar_horas(horas)}\n"
                    
                    if len(usuarios_afetados) > 5:
                        lista_usuarios += f"\n... e mais {len(usuarios_afetados) - 5} usuários"
                    
                    embed.add_field(
                        name="👥 Usuários Resetados",
                        value=lista_usuarios,
                        inline=False
                    )
                
                embed.set_footer(text=f"Ação realizada por {interaction.user.display_name}")
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Erro ao Salvar Alterações",
                    description="Ocorreu um erro ao salvar as alterações no arquivo de horas.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)           
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Erro na Verificação de Arquivados",
            description=f"Ocorreu um erro: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
            
        # Adicionar debug info
        embed.add_field(
            name="🔍 Informações de Debug",
            value=f"Canais na categoria: {len(canais_arquivados)}\n"
                    f"Usuários identificados: {len(todos_usuarios_arquivados)}\n"
                    f"Correspondências com horas: {len(usuarios_com_horas)}",
            inline=False
        )
            
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
        
        # [RESTANTE DO CÓDIGO PARA EXECUÇÃO DA CONFIRMAÇÃO...]
        # (manter o código existente para a parte de confirmação)
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Erro na Verificação de Arquivados",
            description=f"Ocorreu um erro: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="debug_arquivados", description="Debug da categoria de arquivados")
@app_commands.checks.has_permissions(administrator=True)
@verificar_servidor_permitido()
async def debug_arquivados(interaction: discord.Interaction):
    """Debug da categoria de arquivados"""
    await interaction.response.defer(ephemeral=True)
    
    server_config = get_server_config(interaction.guild.id)
    CATEGORIA_ARQUIVADOS_ID = server_config["CATEGORIA_ARQUIVADOS_ID"]
    
    categoria = interaction.guild.get_channel(CATEGORIA_ARQUIVADOS_ID)
    if not categoria:
        await interaction.followup.send("❌ Categoria de arquivados não encontrada.", ephemeral=True)
        return
    
    embed = discord.Embed(title="🔍 Debug - Categoria de Arquivados", color=discord.Color.blue())
    
    # Listar canais
    canais_info = []
    for canal in categoria.channels:
        if isinstance(canal, discord.TextChannel):
            canais_info.append(f"• #{canal.name} (ID: {canal.id})")
    
    embed.add_field(
        name="📂 Canais na categoria",
        value="\n".join(canais_info) if canais_info else "Nenhum canal de texto",
        inline=False
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="minhas_horas", description="Mostra suas horas trabalhadas")
@app_commands.describe(dias="Número de dias para visualizar (padrão: 30)")
@verificar_servidor_permitido()
async def minhas_horas(interaction: discord.Interaction, dias: int = 30):
    """Mostra as horas do usuário"""
    if not await verificar_permissao(interaction, "minhas_horas"):
        # Verificar se o problema é a categoria
        server_config = get_server_config(interaction.guild.id)
        CATEGORIA_ID_HORAS = server_config["CATEGORIA_ID_HORAS"]
        
        if (hasattr(interaction.channel, 'category_id') and 
            interaction.channel.category_id != CATEGORIA_ID_HORAS):
            await interaction.response.send_message(
                f"❌ Este comando só pode ser usado na categoria específica de pontos.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Sem permissão. Você precisa ter o cargo 'Oficina Mecânica' para usar este comando.", 
                ephemeral=True
            )
        return
    
    # CORREÇÃO: Carregar dados do servidor específico
    dados = carregar_horas(interaction.guild.id)
    
    # Tentar encontrar o usuário por diferentes identificadores
    identificadores = [
        interaction.user.display_name,
        f"<@{interaction.user.id}>",
        str(interaction.user.id)
    ]
    
    total_periodo = 0
    registros_usuario = []
    data_limite = (dt.datetime.now() - dt.timedelta(days=dias)).date()
    
    for registro in dados.get("registros", []):
        data_registro = dt.datetime.strptime(registro["data"], "%Y-%m-%d").date()
        
        if data_registro >= data_limite and registro["nome"] in identificadores:
            total_periodo += registro["horas"]
            registros_usuario.append(registro)
    
    if not registros_usuario:
        await interaction.response.send_message(
            f"⚠️ Não foram encontrados registros para você nos últimos {dias} dias.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"⏰ Suas Horas ({dias} dias)",
        color=discord.Color.blue(),
        description=f"**Total: {formatar_horas(total_periodo)}**"
    )
    
    # Agrupar por data
    horas_por_data = {}
    for registro in registros_usuario:
        if registro["data"] not in horas_por_data:
            horas_por_data[registro["data"]] = 0
        horas_por_data[registro["data"]] += registro["horas"]
    
    # Ordenar por data (mais recente primeiro)
    datas_ordenadas = sorted(horas_por_data.keys(), reverse=True)
    
    for data in datas_ordenadas[:7]:  # Mostrar até 7 dias
        embed.add_field(
            name=f"📅 {data}",
            value=formatar_horas(horas_por_data[data]),
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="debug", description="Verifica status do bot")
@verificar_servidor_permitido()
async def debug(interaction: discord.Interaction):
    """Comando de debug"""
    embed = discord.Embed(title="🔧 Debug do Bot", color=discord.Color.blue())
    
    # CORREÇÃO: Verificar arquivos específicos do servidor
    server_config = get_server_config(interaction.guild.id)
    horas_arquivo = server_config["HORAS_ARQUIVO"]
    config_arquivo = server_config["CONFIG_FILE"]
    
    horas_existe = os.path.exists(horas_arquivo)
    config_existe = os.path.exists(config_arquivo)
    
    embed.add_field(name="📁 Arquivo de horas", value=f"{'✅ Existe' if horas_existe else '❌ Não existe'}: {horas_arquivo}", inline=True)
    embed.add_field(name="📁 Arquivo de config", value=f"{'✅ Existe' if config_existe else '❌ Não existe'}: {config_arquivo}", inline=True)
    embed.add_field(name="📁 Diretório atual", value=os.getcwd(), inline=False)
    
    if horas_existe:
        dados = carregar_horas(interaction.guild.id)
        embed.add_field(name="📊 Registros de horas", value=f"{len(dados.get('registros', []))} registros", inline=True)
    
    embed.add_field(name="🎯 Servidor atual", value=f"{interaction.guild.name} (ID: {interaction.guild.id})", inline=True)
    embed.add_field(name="📋 Arquivo usado", value=horas_arquivo, inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    print(f'📁 Diretório atual: {os.getcwd()}')
    
    # Verificar servidores permitidos aqui (quando o bot está realmente pronto)
    servidores_permitidos_encontrados = []
    
    for guild in bot.guilds:
        status = "✅ PERMITIDO" if guild.id in ALLOWED_SERVERS else "❌ NÃO PERMITIDO"
        print(f'   • {guild.name} ({guild.id}) - {status}')
        
        if guild.id in ALLOWED_SERVERS:
            servidores_permitidos_encontrados.append(guild.name)
    
    if servidores_permitidos_encontrados:
        bot.servidores_verificados = True
        print(f"🎯 Servidores permitidos: {', '.join(servidores_permitidos_encontrados)}")
        
        # Executar um processamento IMEDIATO dos dados antes de iniciar as tarefas
        print("🔄 Executando processamento inicial dos dados...")
        try:
            for guild in bot.guilds:
                if guild.id in ALLOWED_SERVERS:
                    server_config = get_server_config(guild.id)
                    CATEGORIA_ID = server_config["CATEGORIA_ID"]
                    
                    print(f"📊 Processando {guild.name} (Arquivo: {server_config['HORAS_ARQUIVO']})")
                    dados = await bot.processar_categoria(guild, CATEGORIA_ID, limite=200)
                    if dados:
                        bot.dados_processados = True
                        print(f"✅ Processamento inicial concluído em {guild.name}")
                        break
        except Exception as e:
            print(f"❌ Erro no processamento inicial: {e}")
        
        # Iniciar tarefas apenas se os dados foram processados
        if bot.dados_processados:
            bot.auto_update.start()
            bot.leaderboard_hourly_update.start()
            
            # CORREÇÃO: Verificar configurações de cada servidor
            for guild in bot.guilds:
                if guild.id in ALLOWED_SERVERS:
                    config_servidor = carregar_configuracoes(guild.id)
                    print(f'🔄 Auto-update em {guild.name}: {"✅ Ativo" if config_servidor["auto_update"]["ativo"] else "❌ Inativo"}')
                    print(f'🏆 Leaderboard update em {guild.name}: {"✅ Ativo" if config_servidor["leaderboard_update"]["ativo"] else "❌ Inativo"}')
        else:
            print("❌ Não foi possível processar dados iniciais. Tarefas não iniciadas.")
    else:
        print("❌ Bot não está em nenhum servidor permitido! Tarefas não iniciadas.")
        bot.servidores_verificados = False

# --- Sincronização de comandos ---
@bot.command()
@commands.has_permissions(administrator=True)
async def sync(ctx):
    """Sincroniza os comandos com o Discord (apenas administradores)"""
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Comandos sincronizados! {len(synced)} comandos disponíveis.")
        print(f"✅ Comandos sincronizados: {len(synced)} comandos")
    except Exception as e:
        await ctx.send(f"❌ Erro ao sincronizar: {e}")
        print(f"❌ Erro na sincronização: {e}")

# --- Executar bot ---
if __name__ == "__main__":
    bot.run(TOKEN)