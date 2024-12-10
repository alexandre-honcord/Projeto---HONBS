# db_utils.py
import cx_Oracle
from django.conf import settings
from datetime import datetime, timedelta


def obter_conexao():
    usuario = settings.DATABASES['oracle']['USER']
    senha = settings.DATABASES['oracle']['PASSWORD']
    ip = settings.DATABASES['oracle']['HOST']
    porta = settings.DATABASES['oracle']['PORT']
    nomedb = settings.DATABASES['oracle']['NAME']


    try:
        connection = cx_Oracle.connect(f"{usuario}/{senha}@{ip}:{porta}/{nomedb}")
        print
        return connection
    except cx_Oracle.DatabaseError as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None
    
def estoque(request):
    connection = obter_conexao()
    if connection is None:
        print("Connection is None in validacao.")  # Log para conexão falha
        return None

    cursor = connection.cursor()
    try:
        sql = """
        select
        SUM(CASE WHEN a.ie_fator_rh = '-' and tasy.obter_result_exam_cde(a.nr_seq_doacao,39)='Negativo' THEN 1
                WHEN a.ie_fator_rh = '-' and tasy.obter_result_exam_cde(a.nr_seq_doacao,39)<>'Negativo' THEN 0
                ELSE 1 END)as qtd,
        a.ds_derivado as tipo,
        a.ie_tipo_sangue||a.ie_fator_rh as fatorRH
        from
        (select 'Reservado' descricao,
        a.cd_estabelecimento,
        a.nr_sangue,
        a.nr_seq_doacao,
        a.nr_seq_derivado,
        a.ds_derivado,
        a.ie_tipo_sangue,
        a.ie_fator_rh,
        a.dt_doacao,
        b.dt_reserva,
        b.nr_atendimento,
        substr(TASY.obter_nome_pessoa_fisica(b.cd_pessoa_fisica,''),1,100) nm_pessoa_fisica,
        a.ie_irradiado,
        a.ie_lavado,
        a.ie_filtrado,
        a.ie_aliquotado,
        TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia) dt_vencimento,
        qt_volume,
        decode(TASY.obter_data_maior(TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia),sysdate),TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia),	'N','S') ie_vencido,
        a.nr_sequencia,
        a.ds_tipo_doacao,
        a.nr_bolsa,
        a.nr_sequencia nr_seq_producao
        FROM	TASY.san_reserva b,
        TASY.san_reserva_prod c,
        TASY.san_producao_consulta_v a
        WHERE 1=1
        and c.nr_seq_reserva = b.nr_sequencia
        AND	a.nr_sequencia = c.nr_seq_producao
        AND	b.ie_status <> 'C'
        AND	a.nr_seq_emp_saida is null
        AND	a.nr_seq_transfusao is null
        AND	a.nr_seq_inutil is null
        AND	nvl(a.ie_encaminhado,'N') = 'N'
        AND	not exists  (SELECT 1
        FROM	TASY.san_envio_derivado_val x,
        TASY.san_envio_derivado z
        WHERE z.nr_sequencia  = x.nr_seq_envio
        AND	x.nr_seq_producao = a.nr_sequencia
        AND	x.dt_recebimento is null)
        AND	not exists (SELECT 1
        FROM	TASY.san_controle_qualidade x,
        TASY.san_controle_qual_prod y
        WHERE x.nr_sequencia = y.nr_seq_qualidade
            AND	y.nr_seq_producao = a.nr_sequencia
            AND	x.dt_liberacao is null)
            AND	not exists (SELECT 1
        FROM	TASY.san_reserva_prod x
        WHERE x.nr_seq_producao = c.nr_seq_producao
            AND	x.ie_status = 'N')
            AND	a.ie_pai_reproduzido <> 'S'
        and  a.nr_seq_derivado not in (12,7)
        AND TRUNC(a.dt_vencimento) >= TRUNC(SYSDATE)
        union
        SELECT 'Estoque',
        a.cd_estabelecimento,
        a.nr_sangue,
        a.nr_seq_doacao,
        a.nr_seq_derivado,
        a.ds_derivado,
        a.ie_tipo_sangue,
        a.ie_fator_rh,
        a.dt_doacao,
        a.dt_producao,
        null,
        '',
        a.ie_irradiado,
        a.ie_lavado,
        a.ie_filtrado,
        a.ie_aliquotado,
        TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia) dt_vencimento,
        qt_volume,
        decode(TASY.Obter_Data_Maior(TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia),sysdate),TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia),'N','S') ie_vencido,
        a.nr_sequencia,
        a.ds_tipo_doacao,
        a.nr_bolsa,
        a.nr_sequencia nr_seq_producao
        FROM TASY.san_producao_consulta_v a
        WHERE 1=1
        and a.dt_liberacao_bolsa is not null
        and a.dt_liberacao is not null
        and a.ie_avaliacao_final = 'A'
        and TASY.obter_se_doacao_exame_pend(a.nr_seq_doacao) = 'N'
        and a.nr_seq_emp_saida is null
            AND	a.nr_seq_transfusao is null
            AND	a.nr_seq_inutil is null
            AND	nvl(a.ie_encaminhado,'N') = 'N'
            AND	not exists (SELECT 1
        FROM	TASY.san_envio_derivado_val x,
        TASY.san_envio_derivado z
        WHERE z.nr_sequencia = x.nr_seq_envio
            AND	x.nr_seq_producao = a.nr_sequencia
            AND	x.dt_recebimento is null)
            AND	not exists (SELECT 1
        FROM	TASY.san_reserva_prod x
        WHERE x.nr_seq_producao = a.nr_sequencia
            AND	x.ie_status <> 'N')
            AND	not exists  (SELECT 1
        FROM TASY.san_controle_qualidade x,
        TASY.san_controle_qual_prod y
        WHERE x.nr_sequencia = y.nr_seq_qualidade
            AND	y.nr_seq_producao = a.nr_sequencia
            AND	x.dt_liberacao is null)
            AND	a.ie_pai_reproduzido <> 'S'  ) a
        WHERE 1 = 1
            AND	 NOT EXISTS (
        SELECT 1
        FROM TASY.san_envio_derivado_val g,
        TASY.san_envio_derivado z
        WHERE z.nr_sequencia  = g.nr_seq_envio
            AND	g.nr_seq_producao = a.nr_sequencia
            AND	 g.dt_recebimento is NULL)
            and a.nr_seq_derivado not in (12,7)
        AND TRUNC(a.dt_vencimento) >= TRUNC(SYSDATE)
        GROUP BY a.ds_derivado,a.ie_tipo_sangue||a.ie_fator_rh
        ORDER BY 3 DESC,2
        """
        cursor.execute(sql)
        estoque = cursor.fetchall()
        return estoque
    except cx_Oracle.DatabaseError as e:
        print(f"Erro ao executar a consulta: {e}")  # Log de erro ao executar a consulta
    finally:
        cursor.close()
        connection.close()

    return None

def lista_estoque(fator_rh=None):
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return []

    cursor = connection.cursor()
    try:
        sql = """
        select
        a.nr_sangue,
        (CASE WHEN a.ie_fator_rh = '-' and tasy.obter_result_exam_cde(a.nr_seq_doacao,39)='Negativo' THEN 1
                WHEN a.ie_fator_rh = '-' and tasy.obter_result_exam_cde(a.nr_seq_doacao,39)<>'Negativo' THEN 0
                ELSE 1 END)qtd,
        nvl(TASY.san_obter_qtd_regra_solic(a.nr_seq_derivado,a.ie_tipo_sangue,a.ie_fator_rh,'MI'),0) qt_estoque_minimo,
        nvl(TASY.san_obter_qtd_regra_solic(a.nr_seq_derivado,a.ie_tipo_sangue,a.ie_fator_rh,'MA'),0) qt_estoque_maximo,
        a.nr_seq_producao,
        a.dt_vencimento,
        case
        when trunc(a.dt_vencimento) = trunc(sysdate) then 'Vence hoje'
        when trunc(a.dt_vencimento) between trunc(sysdate) + 1 and trunc(sysdate) + 30 then 'Vence em 30 dias'
        when trunc(a.dt_vencimento) between trunc(sysdate) + 31 and trunc(sysdate) + 90 then 'Vence em 90 dias'
        when trunc(a.dt_vencimento) > trunc(sysdate) + 90  then 'Vencimento acima de 90 dias'
        end ds_vencimento,
        a.ds_derivado,
        a.ie_tipo_sangue||a.ie_fator_rh sangue,
        tasy.obter_result_exam_cde(a.nr_seq_doacao,39) resultado_exame_CDE,
        a.qt_volume,
        a.ie_filtrado,
        a.ie_irradiado,
        a.ie_lavado,
        a.ie_aliquotado,
        a.descricao local,
        a.nr_atendimento,
        a.nm_pessoa_fisica
        from
        (select 'Reservado' descricao,
        a.cd_estabelecimento,
        a.nr_sangue,
        a.nr_seq_doacao,
        a.nr_seq_derivado,
        a.ds_derivado,
        a.ie_tipo_sangue,
        a.ie_fator_rh,
        a.dt_doacao,
        b.dt_reserva,
        b.nr_atendimento,
        substr(TASY.obter_nome_pessoa_fisica(b.cd_pessoa_fisica,''),1,100) nm_pessoa_fisica,
        a.ie_irradiado,
        a.ie_lavado,
        a.ie_filtrado,
        a.ie_aliquotado,
        TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia) dt_vencimento,
        qt_volume,
        decode(TASY.obter_data_maior(TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia),sysdate),TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia),	'N','S') ie_vencido,
        a.nr_sequencia,
        a.ds_tipo_doacao,
        a.nr_bolsa,
        a.nr_sequencia nr_seq_producao
        FROM	TASY.san_reserva b,
        TASY.san_reserva_prod c,
        TASY.san_producao_consulta_v a
        WHERE 1=1
        and c.nr_seq_reserva = b.nr_sequencia
        AND	a.nr_sequencia = c.nr_seq_producao
        AND	b.ie_status <> 'C'
        AND	a.nr_seq_emp_saida is null
        AND	a.nr_seq_transfusao is null
        AND	a.nr_seq_inutil is null
        AND	nvl(a.ie_encaminhado,'N') = 'N'
        AND	not exists  (SELECT 1
        FROM	TASY.san_envio_derivado_val x,
        TASY.san_envio_derivado z
        WHERE z.nr_sequencia  = x.nr_seq_envio
        AND	x.nr_seq_producao = a.nr_sequencia
        AND	x.dt_recebimento is null)
        AND	not exists (SELECT 1
        FROM	TASY.san_controle_qualidade x,
        TASY.san_controle_qual_prod y
        WHERE x.nr_sequencia = y.nr_seq_qualidade
            AND	y.nr_seq_producao = a.nr_sequencia
            AND	x.dt_liberacao is null)
            AND	not exists (SELECT 1
        FROM	TASY.san_reserva_prod x
        WHERE x.nr_seq_producao = c.nr_seq_producao
            AND	x.ie_status = 'N')
            AND	a.ie_pai_reproduzido <> 'S'
        and  a.nr_seq_derivado not in (12,7)
        AND TRUNC(a.dt_vencimento) >= TRUNC(SYSDATE)
        union
        SELECT 'Estoque',
        a.cd_estabelecimento,
        a.nr_sangue,
        a.nr_seq_doacao,
        a.nr_seq_derivado,
        a.ds_derivado,
        a.ie_tipo_sangue,
        a.ie_fator_rh,
        a.dt_doacao,
        a.dt_producao,
        null,
        '',
        a.ie_irradiado,
        a.ie_lavado,
        a.ie_filtrado,
        a.ie_aliquotado,
        TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia) dt_vencimento,
        qt_volume,
        decode(TASY.Obter_Data_Maior(TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia),sysdate),TASY.San_Obter_Dt_Venc_Producao(a.nr_sequencia),'N','S') ie_vencido,
        a.nr_sequencia,
        a.ds_tipo_doacao,
        a.nr_bolsa,
        a.nr_sequencia nr_seq_producao
        FROM TASY.san_producao_consulta_v a
        WHERE 1=1
        and a.dt_liberacao_bolsa is not null
        and a.dt_liberacao is not null
        and a.ie_avaliacao_final = 'A'
        and TASY.obter_se_doacao_exame_pend(a.nr_seq_doacao) = 'N'
        and a.nr_seq_emp_saida is null
            AND	a.nr_seq_transfusao is null
            AND	a.nr_seq_inutil is null
            AND	nvl(a.ie_encaminhado,'N') = 'N'
            AND	not exists (SELECT 1
        FROM	TASY.san_envio_derivado_val x,
        TASY.san_envio_derivado z
        WHERE z.nr_sequencia = x.nr_seq_envio
            AND	x.nr_seq_producao = a.nr_sequencia
            AND	x.dt_recebimento is null)
            AND	not exists (SELECT 1
        FROM	TASY.san_reserva_prod x
        WHERE x.nr_seq_producao = a.nr_sequencia
            AND	x.ie_status <> 'N')
            AND	not exists  (SELECT 1
        FROM TASY.san_controle_qualidade x,
        TASY.san_controle_qual_prod y
        WHERE x.nr_sequencia = y.nr_seq_qualidade
            AND	y.nr_seq_producao = a.nr_sequencia
            AND	x.dt_liberacao is null)
            AND	a.ie_pai_reproduzido <> 'S'  ) a
        WHERE 1 = 1
            AND	 NOT EXISTS (
        SELECT 1
        FROM TASY.san_envio_derivado_val g,
        TASY.san_envio_derivado z
        WHERE z.nr_sequencia  = g.nr_seq_envio
            AND	g.nr_seq_producao = a.nr_sequencia
            AND	 g.dt_recebimento is NULL)
            and a.nr_seq_derivado not in (12,7)
        AND TRUNC(a.dt_vencimento) >= TRUNC(SYSDATE)
        """
        
        # Adicionar o filtro para `fator_rh`
        params = {}
        if fator_rh:
            sql += " AND a.ie_tipo_sangue || a.ie_fator_rh = :fator_rh"
            params['fator_rh'] = fator_rh
        else:
            print("Sem filtro para fator RH")
            sql += " ORDER BY a.dt_vencimento"

        # Executar consulta com os parâmetros
        cursor.execute(sql, params)

        # Colunas correspondentes à consulta
        keys = [
            "NR_SANGUE", "QTD", "QT_ESTOQUE_MINIMO", "QT_ESTOQUE_MAXIMO", "NR_SEQ_PRODUCAO",
            "DT_VENCIMENTO", "DS_VENCIMENTO", "DS_DERIVADO", "SANGUE", "RESULTADO_EXAME_CDE",
            "QT_VOLUME", "IE_FILTRADO", "IE_IRRADIADO", "IE_LAVADO", "IE_ALIQUOTADO",
            "LOCAL", "NR_ATENDIMENTO", "NM_PESSOA_FISICA"
        ]

        # Obter todas as linhas e mapear para dicionários
        raw_data = cursor.fetchall()
        results = [dict(zip(keys, row)) for row in raw_data]
        return results
    except Exception as e:
        print(f"Erro ao executar a consulta: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

def lista_doacoes(data_inicial=None, data_final=None):
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return []

    cursor = connection.cursor()
    try:
        # Se as datas não forem fornecidas, use o intervalo padrão (últimos 30 dias)
        if not data_inicial:
            data_inicial = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not data_final:
            data_final = datetime.now().strftime('%Y-%m-%d')

        sql = """
        SELECT
            a.nr_bolsa as bolsa,
            TASY.obter_nome_social_pf(a.cd_pessoa_fisica) as doador,
            a.dt_doacao as data,
            TASY.obter_desc_tipo_doacao(a.nr_seq_tipo) as tipo_doacao,
            TASY.obter_valor_dominio(1353, a.ie_tipo_coleta) as tipo_coleta,
            TRUNC(a.dt_retorno) as data_retorno,
            a.qt_altura as altura,
            a.qt_peso as peso,
            a.qt_bpm_pulso as pulso,
            a.qt_temperatura as temperatura,
            a.nr_lote_bolsa as lote,
            a.nr_sangue as sangue,
            a.qt_coletada as volume,
            a.nr_sequencia as sequencia,
            a.nr_seq_isbt as codigo_barras,
            b.ie_tipo_sangue || b.ie_fator_rh as tipo_sangue
        FROM TASY.san_doacao a
        JOIN TASY.pessoa_fisica b ON b.cd_pessoa_fisica = a.cd_pessoa_fisica
        WHERE TRUNC(a.dt_doacao) >= TO_DATE(:data_inicial, 'YYYY-MM-DD')
        AND TRUNC(a.dt_doacao) <= TO_DATE(:data_final, 'YYYY-MM-DD')
        ORDER BY a.dt_doacao DESC
        """

        # Parâmetros para consulta
        params = {
            'data_inicial': data_inicial,
            'data_final': data_final
        }

        # Executar consulta com os parâmetros
        cursor.execute(sql, params)

        # Colunas correspondentes à consulta
        keys = [
            "bolsa",
            "doador",
            "data",
            "tipo_doacao",
            "tipo_coleta",
            "data_retorno",
            "altura",
            "peso",
            "pulso",
            "temperatura",
            "lote",
            "sangue",
            "volume",
            "sequencia",
            "codigo_barras",
            "tipo_sangue"
        ]

        # Obter todas as linhas e mapear para dicionários
        raw_data = cursor.fetchall()
        results = [dict(zip(keys, row)) for row in raw_data]
        return results
    except Exception as e:
        print(f"Erro ao executar a consulta: {e}")
        return []
    finally:
        cursor.close()
        connection.close()