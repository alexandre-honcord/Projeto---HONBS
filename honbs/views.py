from django.shortcuts import redirect
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from honbs.models import User
from django.views.decorators.csrf import csrf_protect
from django.db import IntegrityError
from .backends import exists_ad, tasy_user_data
from django.utils import timezone
from django.contrib.auth.decorators import login_required
import logging
from django.http import JsonResponse
import base64
from django.core.files.base import ContentFile

from honbs.dbutils import estoque, lista_estoque, lista_doacoes
from honbs.utils import format_datetime
from itertools import groupby 
from operator import itemgetter
from datetime import date, datetime

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
    return render(request, 'home.html', context)


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
    return render(request, 'home.html', context)


@login_required
def reports(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'reports.html', context)


@login_required
def donator(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'donator.html', context)

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

    # Contexto para o template
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,
        'doacoes': doacoes_data,
        'data_inicial': data_inicial.isoformat(),
        'data_final': data_final.isoformat(),
    }
    return render(request, 'donations.html', context)

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

    return render(request, 'stock.html', context)

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
    return render(request, 'stock_list.html', context)

@login_required
def fractionation(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'fractionation.html', context)

@login_required
def prodHemocomponente(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'prodHemocomponente.html', context)

@login_required
def batch(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'batch.html', context)

@login_required
def alertas(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'alerts.html', context)

@login_required
def qualidade(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'quality.html', context)


@login_required
def capture(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'capture.html', context)

@login_required
def transfusion(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'transfusion.html', context)

@login_required
def infoTransfusion(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'infoTransfusion.html', context)

@login_required
def dash(request):
    user = request.user
    context = {
        'username': user.username,
        'foto': user.foto.url if user.foto else None,  # Verifica se o usuário tem foto
    }
    return render(request, 'dash.html', context)
