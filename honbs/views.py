import base64
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from itertools import groupby
from operator import itemgetter

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect

from honbs.dbutils import (
    cabecalho_transfusao,
    dados_cabecalho,
    dados_doador,
    estoque,
    exames_lote,
    hemocomponentes,
    hist_doacao,
    lista_captaçao,
    lista_estoque,
    lista_doacoes,
    lista_lotes,
    lista_producao,
    lista_transfusao,
)
from honbs.models import User
from honbs.utils import (
    format_date,
    format_datetime,
    formatar_data_oracle,
    separar_iniciais_por_ponto,
)
from .backends import exists_ad, tasy_user_data
from .models import Drawer, Geladeira

logger = logging.getLogger(__name__)

@csrf_protect
def base_view(request):
    logout_view(request)
    return render(request, 'base.html')

@login_required
def logout_view(request):
    logout(request)  # Desloga o usuário
    response = render(request, 'base.html')
    response.delete_cookie('sessionid')  # Exclui o cookie de sessão
    # Redireciona para a página inicial ou qualquer outra página desejada
    return redirect('base_view')

@login_required
def main(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'inicio/home.html', context)

@csrf_protect
def ldap_login(request):
    if request.method == 'POST':
        username = request.POST.get('user')
        password = request.POST.get('pass')
        # Verifica no LDAP se o usuário existe e a senha é válida
        ldap_response = exists_ad(username, password)
        if ldap_response:
            try:
                user = User.objects.filter(username=username).first()

                if user:
                    user.last_login = timezone.now()
                    user.save()
                    login(request, user)
                else:
                    user = User.objects.create_user(username=username)
                    login(request, user)
                user_data = tasy_user_data(username)
                if user_data:
                    user.IDtasy = user_data.get('IDtasy')
                    user.name = user_data.get('name')
                    if user_data.get('foto') and not user.foto:
                        foto_content = ContentFile(
                            base64.b64decode(user_data['foto']))
                        user.foto.save(f"{username}.jpg", foto_content, save=True)
                    user.save()
                return JsonResponse({'success': True})
            except IntegrityError:
                return JsonResponse({'success': False, 'message': 'Erro ao criar o usuário no banco!'})
        else:
            return JsonResponse({'success': False, 'message': 'Erro! Usuário ou senha incorretos.'})
    return JsonResponse({'success': False, 'message': 'Erro! Entre em contato com o suporte!'})

@login_required
def home(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'inicio/home.html', context)

@login_required
def donator(request, codigo):
    user = request.user

    # Obter os dados do doador pelo código único
    cabecalho_data = dados_cabecalho(codigo)
    
    # Verificar se os dados foram retornados
    if not cabecalho_data:
        return HttpResponseNotFound("Doador não encontrado.")

    # Formatar a data de nascimento
    cabecalho = cabecalho_data[0]
    if "dt_nascimento" in cabecalho:
        cabecalho["dt_nascimento"] = format_datetime(cabecalho["dt_nascimento"])

    # Garantir que 'tipo_sangue' tenha um valor válido
    if "tipo_sangue" not in cabecalho or cabecalho["tipo_sangue"] is None:
        cabecalho["tipo_sangue"] = "#"

    doador_data = dados_doador(codigo)

    for key in doador_data.keys():
        if doador_data[key] is None or doador_data[key] == "":
            doador_data[key] = "N/A"

    if not doador_data:
        return HttpResponseNotFound("Dados do doador não encontrados.")
    
    # Formatar a data de cadastro para datetime-local
    if doador_data.get("cadastro") != "N/A":
        doador_data["cadastro"] = doador_data["cadastro"].strftime("%Y-%m-%dT%H:%M")

    historico_data = hist_doacao(codigo)

    # Verificar e substituir aptidão
    for item in historico_data:
        if item["aptidao"] is None or item["aptidao"] == "A":
            item["aptidao"] = "Apto"
        else:
            item["aptidao"] = "Inapto"

    if not historico_data:
        return HttpResponseNotFound("Dados do doador não encontrados.")

    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,
        'cabecalho': cabecalho,
        'doador_data': doador_data,
        'historico_data': historico_data,
    }
    return render(request, 'doacao/donator.html', context)

@login_required
def donations(request):
    user = request.user

    # Obter filtros de data da requisição
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')

    # Validar e usar a data de hoje como padrão, se necessário
    try:
        if data_inicial:
            data_inicial = datetime.strptime(data_inicial, '%Y-%m-%d').date()
        else:
            data_inicial = date.today()

        if data_final:
            data_final = datetime.strptime(data_final, '%Y-%m-%d').date()
        else:
            data_final = date.today()
    except ValueError as e:
        print(f"Erro ao converter datas: {e}")
        data_inicial = date.today()
        data_final = date.today()

    # Chamar a função para buscar as doações
    doacoes_data = lista_doacoes(data_inicial=data_inicial.isoformat(), data_final=data_final.isoformat())

    # Processar e formatar os dados
    for doacao in doacoes_data:
        if "data" in doacao:
            # Formatar `data` com horas e minutos
            doacao["data"] = format_datetime(doacao["data"], include_time=True)
        if "data_retorno" in doacao:
            # Formatar `data_retorno` apenas com a data
            doacao["data_retorno"] = format_datetime(doacao["data_retorno"])
        for key in ["lote", "tipo_sangue", "altura", "peso", "temperatura", "pulso"]:
            if key in doacao and doacao[key] is None:
                doacao[key] = "N/A"

        # Adicionar uma descrição para o status
        status_map = {0: "Pendente", 1: "Iniciada", 2: "Finalizada"}
        doacao["status_desc"] = status_map.get(doacao.get("status"), "Desconhecido")

    # Separar doações por status
    coletas = [doacao for doacao in doacoes_data if doacao.get("status") == 1]
    triagem = [doacao for doacao in doacoes_data if doacao.get("status") == 0]
    doacoes = [doacao for doacao in doacoes_data if doacao.get("status") >= 0]

    # Contexto atualizado para o template
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,
        'coletas': coletas,
        'triagem': triagem,
        'doacoes': doacoes,
        'data_inicial': data_inicial.isoformat(),
        'data_final': data_final.isoformat(),
    }
    return render(request, 'doacao/donations.html', context)

@login_required
def fractionation(request):
    user = request.user

    # Calcular o intervalo dos últimos 30 dias
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # Chamar a função para buscar as doações
    producoes_data = lista_producao()

    # Processar e formatar os dados
    for producao in producoes_data:
        if "data" in producao:
            producao["data"] = format_datetime(producao["data"], include_time=True)
        if "data_recebimento" in producao:
            producao["data_recebimento"] = format_datetime(producao["data_recebimento"])

    # Chamar a função para buscar os lotes dos últimos 30 dias
    lotes_data = lista_lotes(data_inicial=thirty_days_ago.isoformat(), data_final=today.isoformat())

    # Processar e formatar os dados
    for lote in lotes_data:
        for key in ["inicio", "fim", "geracao", "dt_saida", "dt_chegada"]:
            if key in lote:
                lote[key] = format_datetime(lote[key]) if lote[key] else "N/A"
        for key in ["resp_transporte", "resp_chegada", "temp_chegada"]:
            if key in lote and lote[key] is None:
                lote[key] = "N/A"

    # Contexto atualizado para o template
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,
        'producoes': producoes_data,
        'lotes': lotes_data,
        'data_inicial': thirty_days_ago.isoformat(),
        'data_final': today.isoformat(),
    }
    return render(request, 'fracionamento/fractionation.html', context)

@login_required
def prodHemocomponente(request, codigo):
    user = request.user

    # Obter os dados do doador pelo código único
    hemocomponente_data = hemocomponentes(codigo)

    # Verificar se há resultados e processar as iniciais do doador
    if hemocomponente_data:
        for item in hemocomponente_data:
            item["doador"] = separar_iniciais_por_ponto(item["doador"])

    # Usar o primeiro registro para o header
    hemocomponente = hemocomponente_data[0] if hemocomponente_data else None

    # Ordem predefinida dos exames
    ordem_exames = [
        "Tipo de Sangue ABO",
        "Fator RH",
        "CDE",
        "Pesquisa de Anticorpos Irregulares (PAI)",
        "Doença de Chagas",
        "HBsAg",
        "Anti-HBc Total",
        "Anti-HCV",
        "Anti-HIV 1+2 A",
        "Anti-HIV 1+2 B",
        "Anti HTLV I / II",
        "Sífilis ",
        "Triagem Laboratorial de Hemoglobina ",
        "NAT HIV",
        "NAT HCV",
        "NAT HBV",
    ]

    # Agrupamento de hemocomponentes e exames
    hemocomponentes_unicos = {}
    exames_unicos = defaultdict(lambda: {"resultado": None, "dt_realizado": None})

    if hemocomponente_data:
        for item in hemocomponente_data:
            # Agrupar hemocomponentes por sequência
            hemocomponente_id = item["sequencia"]
            if hemocomponente_id not in hemocomponentes_unicos:
                hemocomponentes_unicos[hemocomponente_id] = {
                    "sequencia": item["sequencia"],
                    "hemocomponente": item["hemocomponente"],
                    "dt_producao": item["dt_producao"],
                    "dt_vencimento": item["dt_vencimento"],
                    "volume": item["volume"],
                    "filtrado": item["filtrado"],
                    "irradiado": item["irradiado"],
                    "aliquotado": item["aliquotado"],
                    "lavado": item["lavado"],
                }
            # Mapear exames com resultado e data de realização
            if item["exame"]:
                exames_unicos[item["exame"]] = {
                    "resultado": item["resultado"],
                    "dt_realizado": item["dt_realizado"],
                }

    # Reorganizar exames na ordem predefinida e adicionar outros no final
    exames_ordenados = []
    for exame in ordem_exames:
        exames_ordenados.append(
            {
                "nome": exame,
                "resultado": exames_unicos[exame]["resultado"],
                "dt_realizado": exames_unicos[exame]["dt_realizado"],
            }
        )
    outros_exames = [
        {
            "nome": exame,
            "resultado": exames_unicos[exame]["resultado"],
            "dt_realizado": exames_unicos[exame]["dt_realizado"],
        }
        for exame in exames_unicos
        if exame not in ordem_exames
    ]
    exames_ordenados.extend(outros_exames)

    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,
        'hemocomponente': hemocomponente,
        'hemocomponente_data': list(hemocomponentes_unicos.values()),
        'exames_ordenados': exames_ordenados,
    }
    return render(request, 'fracionameto/prodHemocomponente.html', context)

@login_required
def batch(request, sequencia):
    user = request.user

    # Verificar se o checkbox foi selecionado para exibir os inativos
    mostrar_inativos = request.GET.get("mostrar_inativos") == "on"

    # Obter os dados do lote
    lote_data = exames_lote(sequencia)

    # Aplicar filtro: Exibir apenas os registros com numeroSangue válido, se não estiver mostrando inativos
    if not mostrar_inativos:
        lote_data = [item for item in lote_data if item["numeroSangue"]]

    # Agrupar os dados por NR_SEQ_EXAME_LOTE
    grouped_data = {}
    for item in lote_data:
        numeroSangue = item["numeroSangue"] or "N/A"  # Definir um valor padrão para casos None
        key = item["NR_SEQ_EXAME_LOTE"]
        if key not in grouped_data:
            grouped_data[key] = {
                "NR_SEQ_EXAME_LOTE": key,
                "NR_SEQ_LOTE": item["NR_SEQ_LOTE"],
                "numeroSangue": numeroSangue,
                "exames": []
            }
        grouped_data[key]["exames"].append({
            "NR_SEQUENCIA": item["NR_SEQUENCIA"],
            "NR_SEQ_EXAME": item["NR_SEQ_EXAME"],
            "ie_resultado": item["ie_resultado"],
        })

    # Converter para uma lista para facilitar o uso no template
    grouped_data = list(grouped_data.values())

    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,
        'grouped_data': grouped_data,
        'mostrar_inativos': mostrar_inativos,
    }
    return render(request, 'fracionamento/batch.html', context)

@login_required
def liberation(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None
    }
    return render(request, 'liberacao/liberation.html', context)

@login_required
def transfusion(request):
    user = request.user

    # Datas de ontem e hoje no formato esperado pelo Oracle
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Formatar as datas como DD/MM/YYYY
    today_formatted = today.strftime('%d/%m/%Y')
    yesterday_formatted = yesterday.strftime('%d/%m/%Y')

    # Chamar a função para buscar as transfusões de ontem e hoje
    transfusao_data = lista_transfusao(data_inicial=yesterday_formatted, data_final=today_formatted)

    for transfusao in transfusao_data:
        for key, value in transfusao.items():
            if value is None:
                transfusao[key] = "N/A"
        if "DT_INF_INICIADA" in transfusao:
            transfusao["DT_INF_INICIADA"] = formatar_data_oracle(transfusao["DT_INF_INICIADA"])

    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  
        'transfusao_data': transfusao_data,
    }
    return render(request, 'transfusao/transfusion.html', context)

@login_required
def infoTransfusion(request, codigo):
    user = request.user

    # Datas de ontem e hoje no formato esperado pelo Oracle
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Formatar as datas como DD/MM/YYYY
    today_formatted = today.strftime('%d/%m/%Y')
    yesterday_formatted = yesterday.strftime('%d/%m/%Y')

    # Chamar a função para buscar as transfusões de ontem e hoje
    transfusao_data = lista_transfusao(data_inicial=yesterday_formatted, data_final=today_formatted)

    # Tratar valores nulos no transfusao_data
    for transfusao in transfusao_data:
        for key, value in transfusao.items():
            if value is None:
                transfusao[key] = "N/A"
        if "DS_NASCIMENTO" in transfusao:
            transfusao["DS_NASCIMENTO"] = format_date(transfusao["DS_NASCIMENTO"], include_time=True)

    header = cabecalho_transfusao(codigo)

    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  
        'transfusao_data': transfusao_data,
        'header': header,
    }
    return render(request, 'transfusao/infoTransfusion.html', context)

@login_required
def reserve(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'transfusao/reserve.html', context)

@login_required
def stock(request):
    user = request.user
    consulta_estoque = []
    consulta_agrupada = {}
    total_geral_bolsas = 0

    # Estoque total personalizado para cada fator RH
    estoque_total_por_fator = {
        'A+': 500,
        'A-': 100,
        'B+': 200,
        'B-': 50,
        'AB+': 100,
        'AB-': 30,
        'O+': 600,
        'O-': 100,
    }

    # Ordem desejada dos fatores RH
    ordem_fator_rh = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']

    # Executa a consulta
    consulta_estoque = estoque(request)  # Chama a função estoque

    if consulta_estoque:
        # Transformar em lista de dicionários
        consulta_estoque = [
            {'qtd': row[0], 'tipo_bolsa': row[1], 'fator_rh': row[2]}
            for row in consulta_estoque
        ]

        # Agrupar por fator RH
        for fator_rh, items in groupby(sorted(consulta_estoque, key=itemgetter('fator_rh')), key=itemgetter('fator_rh')):
            bolsas = list(items)
            soma_total = sum(bolsa['qtd'] for bolsa in bolsas)  # Soma total por fator RH
            total_geral_bolsas += soma_total  # Adiciona ao total geral
            total_fator_rh = estoque_total_por_fator.get(fator_rh, 500)  # Pega o total ou usa 500 como padrão
            porcentagem = round((soma_total / total_fator_rh) * 100, 2)  # Calcula a porcentagem
            consulta_agrupada[fator_rh] = {
                'bolsas': bolsas,
                'soma_total': soma_total,
                'estoque_total': total_fator_rh,
                'porcentagem': porcentagem
            }

    # Reorganizar os dados agrupados de acordo com a ordem desejada
    consulta_agrupada_ordenada = {
        fator_rh: consulta_agrupada[fator_rh]
        for fator_rh in ordem_fator_rh
        if fator_rh in consulta_agrupada
    }

    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,
        'estoque': consulta_agrupada_ordenada,  # Dados agrupados ordenados
        'total_geral_bolsas': total_geral_bolsas,  # Total geral de bolsas
    }

    return render(request, 'estoque/stock.html', context)

@login_required
def stock_list(request):
    user = request.user
    fator_rh = request.GET.get('fator_rh')

    stock_data = lista_estoque(fator_rh=fator_rh)

    # Processar e formatar os dados
    for stock in stock_data:
        # Garantir que today seja um objeto date
        today = datetime.now().date()

        # Garantir que vencimento seja um objeto date
        if isinstance(stock["DT_VENCIMENTO"], datetime):
            vencimento = stock["DT_VENCIMENTO"].date()
        else:
            vencimento = datetime.strptime(stock["DT_VENCIMENTO"], "%Y-%m-%d").date()

        # Calcular os dias para o vencimento
        days_to_expiry = (vencimento - today).days

        # Determinar o texto e a classe da linha com base nos dias para o vencimento
        if days_to_expiry < 7:
            stock["row_class"] = "danger"
            stock["EXPIRY_TEXT"] = "Menos que 7 dias"
        elif days_to_expiry < 30:
            stock["row_class"] = "light-red"
            stock["EXPIRY_TEXT"] = "Menos que 30 dias"
        elif days_to_expiry < 90:
            stock["row_class"] = "light-yellow"
            stock["EXPIRY_TEXT"] = "Menos que 90 dias"
        else:
            stock["row_class"] = "light-green"
            stock["EXPIRY_TEXT"] = "Mais que 90 dias"

        stock["DT_VENCIMENTO"] = format_datetime(stock["DT_VENCIMENTO"])
        for key in ["IE_FILTRADO", "IE_IRRADIADO", "IE_LAVADO", "IE_ALIQUOTADO", "NR_ATENDIMENTO", "NM_PESSOA_FISICA", "RESULTADO_EXAME_CDE"]:
            if stock[key] == "N":
                stock[key] = '<i class="fas fa-times-circle" style="color: red;"></i>'
            elif stock[key] == "S":
                stock[key] = '<i class="fas fa-check-circle" style="color: green;"></i>'
            elif stock[key] is None:
                stock[key] = "N/A"

    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,
        'stocks': stock_data,
        'fator_rh': fator_rh,
    }
    return render(request, 'estoque/stock_list.html', context)

@login_required
def capture(request):
    user = request.user

    # Obter os dados do doador
    captacao_data = lista_captaçao()

    # Formatar datas e tratar valores nulos
    for doador in captacao_data:
        if "dt_doacao" in doador:
            doador["dt_doacao"] = format_date(doador["dt_doacao"])
        if "tipo_sangue" not in doador or doador["tipo_sangue"] is None:
            doador["tipo_sangue"] = "#"

    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,
        'captacao_data': captacao_data,
    }
    return render(request, 'captacao/capture.html', context)

@login_required
def qualidade(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'qualidade/quality.html', context)

@login_required
def reports(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'relatorios/reports.html', context)

@login_required
def alertas(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'alertas/alerts.html', context)

# @login_required
# def registrations(request):
#     user = request.user

#     if request.method == "POST":
#         try:
#             if 'add_fridge' in request.POST:
#                 nome = request.POST.get('nome')
#                 quantidade_prateleiras = int(request.POST.get('quantidade_prateleiras', 0))
#                 if not nome or quantidade_prateleiras <= 0:
#                     messages.error(request, "Todos os campos da geladeira são obrigatórios.")
#                 else:
#                     Fridge.objects.create(
#                         nome=nome,
#                         quantidade_prateleiras=quantidade_prateleiras
#                     )
#                     messages.success(request, "Geladeira cadastrada com sucesso.")
#                     return redirect('registrations')

#             elif 'add_stock' in request.POST:
#                 fridge_id = request.POST.get('fridge_id')
#                 prateleira_id = int(request.POST.get('prateleira_id', 0))
#                 hemocomponente_id = request.POST.get('hemocomponente_id')
#                 quantidade = int(request.POST.get('quantidade', 0))

#                 fridge = Fridge.objects.filter(id=fridge_id).first()
#                 if not fridge:
#                     messages.error(request, "Geladeira selecionada não existe.")
#                 elif prateleira_id <= 0 or not hemocomponente_id:
#                     messages.error(request, "Todos os campos de estoque são obrigatórios.")
#                 else:
#                     HemocomponentStock.objects.create(
#                         fridge=fridge,
#                         prateleira_id=prateleira_id,
#                         hemocomponente_id=hemocomponente_id,
#                         quantidade=quantidade  
#                     )
#                     messages.success(request, "Estoque de hemocomponente cadastrado com sucesso.")
#                     return redirect('registrations')
#         except ValueError as e:
#             messages.error(request, f"Erro ao processar o formulário: {e}")

#     # Agrupar o estoque por geladeira
#     stock_data = defaultdict(list)
#     for stock in HemocomponentStock.objects.select_related('fridge').all():
#         stock_data[stock.fridge].append({
#             'prateleira_id': stock.prateleira_id,
#             'hemocomponente_id': stock.hemocomponente_id,
#             'quantidade': stock.quantidade,
#         })

#     context = {
#         'username': user.username,
#         'foto': user.foto.url if user.foto else None,
#         'geladeiras': Fridge.objects.all(),
#         'hemocomponentes': HemocomponentStock.objects.all(),
#         'stock_data': dict(stock_data),  # Passa os dados agrupados
#     }

#     return render(request, 'cadastros/registrations.html', context)

# @login_required
# def edit_stock(request, hemocomponente_id):
#     stock = get_object_or_404(HemocomponentStock, hemocomponente_id=hemocomponente_id)

#     if request.method == "POST":
#         fridge_id = request.POST.get("fridge_id")
#         prateleira_id = request.POST.get("prateleira_id")        
#         stock.fridge_id = fridge_id
#         stock.prateleira_id = prateleira_id
#         stock.save()
#         messages.success(request, "Estoque atualizado com sucesso!")
#         return redirect("registrations")

#     geladeiras = Fridge.objects.all()  # Para preencher o dropdown
#     context = {
#         "stock": stock,
#         "geladeiras": geladeiras,
#     }
#     return render(request, "edit_stock.html", context)

# @login_required
# def delete_stock(request, hemocomponente_id):
#     stocks = HemocomponentStock.objects.filter(hemocomponente_id=hemocomponente_id)

#     if request.method == "POST":
#         count = stocks.count()  # Conta quantos registros serão apagados
#         stocks.delete()
#         messages.success(request, f"{count} registro(s) de estoque apagado(s) com sucesso!")
#         return redirect("registrations")

#     context = {"stocks": stocks}
#     return render(request, "delete_stock.html", context)

@login_required
def autoexclude(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'exclusao/autoexclude.html', context)

@login_required
def autoexclusion(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'exclusao/autoexclusion.html', context)

@login_required
def exclusionDados(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'exclusao/exclusionDados.html', context)

scanned_items = {}

def inventory(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,
        'fridges': Geladeira.objects.all(),  # Lista as 5 geladeiras fixas
    }
    return render(request, "inventario/inventory.html", context)

def fridge_detail(request, fridge_id):
    user = request.user
    fridge = get_object_or_404(Geladeira, id=fridge_id)
    
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,
        'fridge': fridge,
        'drawers': fridge.drawers.all(),
    }
    return render(request, "inventario/fridge_detail.html", context)


