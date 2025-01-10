# db_utils.py
import cx_Oracle
from django.conf import settings
from datetime import date, datetime, timedelta


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

        # Ordenação pelo vencimento
        sql += " ORDER BY a.dt_vencimento ASC"

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
            a.cd_pessoa_fisica as codigo,
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
            b.ie_tipo_sangue || b.ie_fator_rh as tipo_sangue,
            a.ie_status as status
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
            "codigo",
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
            "tipo_sangue",
            "status"
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

def lista_producao():
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return []

    cursor = connection.cursor()
    try:
        sql = """
        SELECT
            a.nr_sequencia as codigo,
            SUBSTR(TASY.obter_iniciais_nome(a.cd_pessoa_fisica,NULL),1,50) as doador,
            a.cd_pessoa_fisica||'/'||SUBSTR(TASY.san_qtd_doacao_coletada(a.cd_pessoa_fisica),1,50) doacoes,
            c.ds_tipo_doacao as tipoDoacoes,
            a.dt_doacao as data,
            a.nr_sangue as numeroSangue,
            a.nr_bolsa as numeroBolsa,
            a.nr_lote_bolsa as loteBolsa,
            SUBSTR(TASY.obter_valor_dominio(2176,ie_tipo_bolsa),1,100) tipoBolsa,
            DECODE(a.IE_REALIZA_NAT, 'S', TASY.obter_desc_expressao(719927), TASY.obter_desc_expressao(327114)) teste_acido_nucleico,
            SUBSTR(TASY.san_obter_desc_anticoagulante(a.nr_seq_antic),1,255) anticoalugante,
            SUBSTR(TASY.obter_valor_dominio(1353,a.ie_tipo_coleta),1,255) tipo_coleta,
            NVL(a.qt_volume_atual,a.qt_coletada) as volume,
            DECODE(SUBSTR(TASY.Obter_Sexo_PF(a.cd_pessoa_fisica, 'C'),1,10), 'M', TASY.obter_desc_expressao(292932), TASY.obter_desc_expressao(290058)) sexo,
            DECODE(a.IE_AVALIACAO_FINAL, 'A', TASY.obter_desc_expressao(283718), 'I', TASY.obter_desc_expressao(309592)) apto,
            DECODE(a.ie_dms, 'S', TASY.obter_desc_expressao(719927), TASY.obter_desc_expressao(327114)) descarte,
            DECODE(SUBSTR(TASY.san_obter_se_produzido(a.nr_sequencia),1,1), 'S', TASY.obter_desc_expressao(719927), TASY.obter_desc_expressao(327114)) produzido,
            a.qt_min_coleta as tempoColeta,
            SUBSTR(TASY.obter_nome_pf(a.cd_pessoa_coleta),1,150) coletor,
            a.nr_conector as conector,
            DECODE(NVL(a.ie_fracionar_bolsa,'S'), 'S', TASY.obter_desc_expressao(719927), TASY.obter_desc_expressao(327114)) fracionar_bolsa,
            a.nm_usuario_recebimento as usuarioRecebimento,
            a.dt_recebimento_bolsa as dtRecebimento,
            a.nr_sequencia as sequencia,
            DECODE(SUBSTR(TASY.san_obter_se_doador_trali(a.cd_pessoa_fisica),1,1), 'S', TASY.obter_desc_expressao(719927), TASY.obter_desc_expressao(327114)) trali,
            DECODE(SUBSTR(TASY.obter_se_doadora_multigesta(a.nr_sequencia),1,1), 'S', TASY.obter_desc_expressao(719927), TASY.obter_desc_expressao(327114)) ie_multigesta,
            TASY.OBTER_ISBT_DOADOR(a.nr_sequencia, null, 'D') as ISBT
        FROM
            TASY.san_tipo_doacao c,
            TASY.san_doacao a
        WHERE
            a.nr_seq_tipo = c.nr_sequencia 
        AND	a.ie_status >= 2 
        AND	a.ie_tipo_coleta <> 2 
        AND	((a.ie_dms = 'S' 
        AND	a.dt_inutilizacao is null) OR (a.ie_dms = 'N' OR a.ie_dms is null))   
        AND	a.cd_estabelecimento = 1  
        AND	nvl(a.ie_auto_exclusao, 'N') = 'N'  
        AND	a.ie_avaliacao_final <> 'I'  
        AND	a.dt_doacao > sysdate - 30 
        AND	a.cd_estabelecimento = 1
        AND	not exists   (SELECT 1  
        FROM	 TASY.san_producao z  
        WHERE z.nr_seq_doacao = a.nr_sequencia  
            AND	z.dt_liberacao is not null  ) 
            AND	a.dt_fim_prod_doacao is null 
        ORDER BY a.dt_doacao desc
        """

        # Executar consulta com os parâmetros
        cursor.execute(sql)

        # Colunas correspondentes à consulta
        keys = [
            "codigo",
            "doador",
            "doacoes",
            "tipo_doacoes",
            "data",
            "numero_sangue",
            "numero_bolsa",
            "lote_bolsa",
            "tipo_bolsa",
            "teste_acido_nucleico",
            "anticoagulante",
            "tipo_coleta",
            "volume",
            "sexo",
            "apto",
            "descarte",
            "produzido",
            "tempo_coleta",
            "coletor",
            "conector",
            "fracionar_bolsa",
            "usuario_recebimento",
            "data_recebimento",
            "sequencia",
            "trali",
            "ie_multigesta",
            "isbt"
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

def hemocomponentes(codigo):
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return []

    cursor = connection.cursor()
    try:
        sql = """
        SELECT
            a.cd_pessoa_fisica as codigo,
            SUBSTR(TASY.obter_iniciais_nome(a.cd_pessoa_fisica,NULL),1,50) as doador,
            a.nr_sangue as numeroSangue,
            a.nr_bolsa as numeroBolsa,
            DECODE(SUBSTR(TASY.Obter_Sexo_PF(a.cd_pessoa_fisica, 'C'),1,10), 'M', TASY.obter_desc_expressao(292932), TASY.obter_desc_expressao(290058)) sexo,
            b.nr_sequencia as sequencia,
            TASY.obter_desc_hemocomponente(b.nr_seq_derivado) as hemocomponente,
            b.dt_producao as dt_producao,
            b.dt_vencimento as dt_vencimento,
            a.qt_volume_real as volume,
            b.ie_filtrado as filtrado,
            b.ie_irradiado as irradiado,
            b.ie_aliquotado as aliquotado,
            b.ie_lavado as lavado,
            TASY.san_obter_desc_exame(d.nr_seq_exame) as exame,
            d.ds_resultado as resultado,
            d.dt_realizado as dt_realizado
        FROM TASY.san_doacao a
        JOIN TASY.san_producao b ON b.nr_sangue = a.nr_sangue
        JOIN TASY.san_exame_lote c ON c.nr_seq_doacao = a.nr_sequencia
        JOIN TASY.san_exame_realizado d ON d.nr_seq_exame_lote = c.nr_sequencia
        WHERE
            a.nr_bolsa = :codigo
        ORDER BY a.dt_doacao DESC
        """

        # Executar consulta com o código como parâmetro
        params = {'codigo': codigo}
        cursor.execute(sql, params)

        # Colunas correspondentes à consulta
        keys = [
            "codigo",
            "doador",
            "numero_sangue",
            "numero_bolsa",
            "sexo",
            "sequencia",
            "hemocomponente",
            "dt_producao",
            "dt_vencimento",
            "volume",
            "filtrado",
            "irradiado",
            "aliquotado",
            "lavado",
            "exame",
            "resultado",
            "dt_realizado"
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

def lista_lotes(data_inicial=None, data_final=None):
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return []

    cursor = connection.cursor()
    try:
        # Se as datas não forem fornecidas, use o intervalo padrão (mês atual)
        if not data_inicial:
            today = date.today()
            data_inicial = today.replace(day=1).strftime('%Y-%m-%d')  # Primeiro dia do mês atual

        if not data_final:
            data_final = date.today().strftime('%Y-%m-%d')  # Data atual

        sql = """
        SELECT
            a.nr_sequencia as sequencia,
            TASY.obter_qtd_exame_lote_hemo(a.nr_sequencia) as qt_amostras,
            a.dt_inicio as inicio,
            a.dt_fim as fim,
            a.dt_geracao as geracao,
            a.dt_saida_bs as dt_saida,
            a.qt_temp_transp as temp_saida,
            TASY.OBTER_NOME_PF(a.cd_resp) as resp_saida,
            a.dt_chegada_local as dt_chegada,
            a.qt_temp_chegada as temp_chegada,
            TASY.OBTER_NOME_PF(a.nm_resp_local) as resp_chegada,
            a.nm_resp_transporte as resp_transporte
        FROM
            TASY.san_lote_hemoterapia a
        WHERE TRUNC(a.dt_inicio) >= TO_DATE(:data_inicial, 'YYYY-MM-DD')
        AND TRUNC(a.dt_fim) <= TO_DATE(:data_final, 'YYYY-MM-DD')
        ORDER BY a.dt_inicio DESC
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
            "sequencia",
            "qt_amostras",
            "inicio",
            "fim",
            "geracao",
            "dt_saida",
            "temp_saida",
            "resp_saida",
            "dt_chegada",
            "temp_chegada",
            "resp_chegada",
            "resp_transporte"
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

def dados_cabecalho(codigo):
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return []

    cursor = connection.cursor()
    try:
        sql = """
            SELECT
                a.nm_pessoa_fisica as nome,
                TASY.obter_nome_mae_pf(a.cd_pessoa_fisica) as nome_mae,
                a.dt_nascimento,
                DECODE(SUBSTR(TASY.Obter_Sexo_PF(b.cd_pessoa_fisica, 'C'),1,10), 'M', TASY.obter_desc_expressao(292932), TASY.obter_desc_expressao(290058)) sexo,
                a.ie_tipo_sangue || a.ie_fator_rh as tipo_sangue
            FROM TASY.pessoa_fisica a
            JOIN TASY.san_doacao b ON b.cd_pessoa_fisica = a.cd_pessoa_fisica
            WHERE
                a.cd_pessoa_fisica = :codigo
        """

        # Executar consulta com o código como parâmetro
        params = {'codigo': codigo}
        cursor.execute(sql, params)

        keys = [
            "nome",
            "nome_mae",
            "dt_nascimento",
            "sexo",
            "tipo_sangue",
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

def dados_doador(codigo):
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return {}

    cursor = connection.cursor()
    try:
        sql = """
            SELECT
                a.nm_pessoa_fisica as nome,
                TASY.obter_desc_profissao(b.cd_profissao) as profissao,
                TASY.obter_nome_pai_mae(a.cd_pessoa_fisica, 'M') as nome_mae,
                TASY.obter_nome_pai_mae(a.cd_pessoa_fisica, 'P') nome_pai,
                a.dt_nascimento as nascimento,
                TASY.obter_dados_pf(a.cd_pessoa_fisica, 'N') as nacionalidade,
                DECODE(SUBSTR(TASY.Obter_Sexo_PF(b.cd_pessoa_fisica, 'C'),1,10), 'M', TASY.obter_desc_expressao(292932), TASY.obter_desc_expressao(290058)) sexo,
                TASY.obter_valor_dominio(5, a.ie_estado_civil) as estado_civil,
                TASY.obter_dados_pf(a.cd_pessoa_fisica, 'CP') as cor_pele,
                a.nr_cpf as cpf,
                a.nr_identidade as rg,
                a.ds_orgao_emissor_ci as orgaoEmissor,
                a.ds_observacao as observacao,
                a.dt_cadastro_original as cadastro,
                a.nm_usuario_original as usuario_cadastro,
                a.nr_telefone_celular as telefone1,
                b.nr_telefone as telefone2,
                b.ds_email as email,
                b.cd_cep as cep,
                b.ds_endereco as logradouro,
                b.ds_complemento as complemento,
                b.nr_endereco as numero,
                b.ds_municipio as cidade,
                b.sg_estado as estado,
                c.nm_pais as pais,
                a.ie_tipo_sangue as tipoSangue,
                a.ie_fator_rh as fatorRH,
                substr(TASY.san_ultimo_fenotipo_pf(a.cd_pessoa_fisica,'N'),1,255) as fenotipo
            FROM TASY.pessoa_fisica a
            JOIN TASY.compl_pessoa_fisica b ON b.cd_pessoa_fisica = a.cd_pessoa_fisica
            JOIN TASY.pais c on c.nr_sequencia = b.nr_seq_pais
            WHERE
                a.cd_pessoa_fisica = :codigo
            AND
                ROWNUM = 1
        """

        params = {'codigo': codigo}
        cursor.execute(sql, params)

        keys = [
            "nome",
            "profissao",
            "nome_mae",
            "nome_pai",
            "nascimento",
            "nacionalidade",
            "sexo",
            "estado_civil",
            "cor_pele",
            "cpf",
            "rg",
            "orgao_emissor",
            "observacao",
            "cadastro",
            "usuario_cadastro",
            "telefone1",
            "telefone2",
            "email",
            "cep",
            "logradouro",
            "complemento",
            "numero",
            "cidade",
            "estado",
            "pais",
            "tipoSangue",
            "fatorRH",
            "fenotipo"
        ]

        raw_data = cursor.fetchall()
        results = [dict(zip(keys, row)) for row in raw_data]
        return results[0] if results else {}
    except Exception as e:
        print(f"Erro ao executar a consulta: {e}")
        return {}
    finally:
        cursor.close()
        connection.close()

def hist_doacao(codigo):
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return []

    cursor = connection.cursor()
    try:
        sql = """
            SELECT
                a.nr_sequencia as numDoacao,
                TASY.obter_desc_tipo_doacao(a.nr_seq_tipo) as tipo_doacao,
                a.dt_doacao as data,
                a.ie_avaliacao_final
            FROM TASY.san_doacao a
            WHERE
                a.cd_pessoa_fisica = :codigo
            ORDER BY a.dt_doacao DESC
        """

        # Executar consulta com o código como parâmetro
        params = {'codigo': codigo}
        cursor.execute(sql, params)

        keys = [
            "numDoacao",
            "tipo_doacao",
            "data",
            "aptidao"
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

def exames_lote(sequencia):
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return []

    cursor = connection.cursor()
    try:
        sql = """
            SELECT  
                b.NR_SEQUENCIA,	
                b.NR_SEQ_LOTE,
                b.NR_SEQ_EXAME_LOTE,
                TASY.san_obter_desc_exame(b.NR_SEQ_EXAME),
                g.ie_resultado,
                e.nr_bolsa as numeroSangue
            FROM	  
                TASY.san_doacao e,
                TASY.san_exame g,
                TASY.san_exame_lote c,
                TASY.san_exame_realizado d,
                TASY.san_lote_hemoterapia a,
                TASY.SAN_LOTE_HEMOTERAPIa_item b,
                TASY.san_tipo_doacao f
            WHERE   a.nr_sequencia  = b.nr_Seq_lote
            and  c.nr_sequencia  = b.nr_seq_exame_lote
            and  d.nr_seq_exame_lote  = c.nr_sequencia 
            and  b.nr_seq_exame  = d.nr_seq_exame
            and b.nr_seq_lote   = :sequencia
            and d.nr_seq_exame  = g.nr_sequencia
            and  b.nr_seq_exame_lote  = d.nr_seq_exame_lote   
            and  c.nr_seq_doacao  = e.nr_sequencia(+) 
            and  f.nr_sequencia(+)  = e.nr_seq_tipo 
            ORDER BY  b.nr_sequencia
        """

        # Executar consulta com o código como parâmetro
        params = {'sequencia': sequencia}
        cursor.execute(sql, params)

        keys = [
            "NR_SEQUENCIA",
            "NR_SEQ_LOTE",
            "NR_SEQ_EXAME_LOTE",
            "NR_SEQ_EXAME",
            "ie_resultado",
            "numeroSangue"
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

def lista_transfusao(data_inicial=None, data_final=None):
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return []

    cursor = connection.cursor()
    try:
        # Se as datas não forem fornecidas, use um intervalo padrão (ontem e hoje)
        if not data_inicial or not data_final:
            today = date.today()
            yesterday = today - timedelta(days=1)
            data_inicial = yesterday.strftime('%d/%m/%Y')
            data_final = today.strftime('%d/%m/%Y')

        sql = """
        SELECT
            CD_PESSOA_FISICA,
            SUBSTR(TASY.obter_nome_pf(CD_PESSOA_FISICA), 1, 50) NM_RECEPTOR,    
            TASY.obter_nome_pai_mae(cd_pessoa_fisica, 'M') as nome_mae,
            SUBSTR(TASY.obter_descricao_padrao('PESSOA_FISICA', 'IE_TIPO_SANGUE', CD_PESSOA_FISICA), 1, 2) ||
            SUBSTR(TASY.obter_dados_pf(cd_pessoa_fisica, 'DSRH'), 1, 10) DS_SANGUE,
            TASY.obter_data_nascto_pf(cd_pessoa_fisica) DS_NASCIMENTO,
            SUBSTR(TASY.obter_dados_pf(cd_pessoa_fisica, 'I'), 1, 25) DS_IDADE,
            SUBSTR(TASY.OBTER_NOME_CONVENIO(TASY.obter_convenio_atendimento(nr_atendimento)), 1, 25) DS_CONVENIO,
            SUBSTR(TASY.obter_se_houve_reacao_trans(cd_pessoa_fisica, null), 1, 10) IE_REACAO,
            SUBSTR(DECODE(TASY.obter_se_houve_reacao_trans(cd_pessoa_fisica, null), 'S',
            TASY.obter_desc_expressao(719927), 'N', TASY.obter_desc_expressao(327114)), 1, 255) DS_IE_REACAO,
            SUBSTR(TASY.obter_nome_pf(CD_MEDICO_REQUISITANTE), 1, 50) NM_MEDICO_REQUISITANTE,
            SUBSTR(TASY.obter_nome_pf(CD_PF_REALIZOU), 1, 50) NM_PF_REALIZOU,
            SUBSTR(TASY.san_obter_cor_reserva_trans(nr_seq_classif, 'CLAS'), 1, 150) DS_CLASSIF_COR_TRANS,
            DECODE(IE_CONTA_GERADA, 'S', TASY.obter_desc_expressao(719927), TASY.obter_desc_expressao(327114)) DS_IE_CONTA_GERADA,
            DECODE(SUBSTR(TASY.san_obter_se_amostra_valida(CD_PESSOA_FISICA), 1, 1), 'S',
            TASY.obter_desc_expressao(719927), TASY.obter_desc_expressao(327114)) IE_POSSUI_AMOSTRA,
            SUBSTR(TASY.obter_unidade_atendimento(nr_atendimento, 'IAA', 'S'), 1, 50) DS_SETOR_UNIDADE,
            SUBSTR(TASY.san_ultimo_fenotipo_pf(cd_pessoa_fisica, 'N'), 1, 255) DS_FENOTIPO,
            SUBSTR(TASY.san_ultimo_fenotipo_pf(cd_pessoa_fisica, 'N', 1), 1, 255) DS_FENOTIPO_PADRAO,
            DECODE(TASY.obter_qt_pend_paciente(nr_seq_reserva), 0, TASY.obter_desc_expressao(327114), TASY.obter_desc_expressao(719927)) IE_PEND_PACIENTE,
            SUBSTR(TASY.Obter_se_transfusao_iniciada(nr_sequencia), 1, 1) IE_TRANSF_INICIADA,
            TASY.obter_se_prescricao_suspensa(NR_PRESCRICAO) IE_PRESCR_SUSP,
            TASY.obter_inf_producao_reserva(NR_SEQUENCIA, 'DI') DT_INF_INICIADA,
            SUBSTR(TASY.san_obter_cor_reserva_trans(nr_seq_classif, 'COR'), 1, 150) DS_COR,
            SUBSTR(TASY.obter_se_houve_reacao(nr_sequencia, null), 1, 1) IE_HOUVE_REACAO,
            SUBSTR(TASY.chk_dispensar_sanprodu_sts(nr_sequencia), 1, 1) CHK_DT_DISPENSACAO,
            SUBSTR(TASY.san_possui_prod_utilizada(nr_sequencia, 'T'), 1, 1) IE_POSSUI_PROD_UTIL
        FROM TASY.SAN_TRANSFUSAO a
        WHERE 1 = 1 
            AND SUBSTR(TASY.san_obter_se_amostra_valida(CD_PESSOA_FISICA), 1, 1) = 'S'
            AND ((TASY.obter_qt_pend_paciente(nr_seq_reserva) > 0 AND 'N' = 'S') OR ('N' = 'N'))
            AND a.cd_estabelecimento = 1 
            AND a.dt_transfusao BETWEEN TO_DATE(:data_inicial, 'DD/MM/YYYY') 
            AND TO_DATE(:data_final, 'DD/MM/YYYY')
        ORDER BY DT_TRANSFUSAO DESC
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
            "CD_PESSOA_FISICA",
            "NM_RECEPTOR",
            "nome_mae",
            "DS_SANGUE",
            "DS_NASCIMENTO",
            "DS_IDADE",
            "DS_CONVENIO",
            "IE_REACAO",
            "DS_IE_REACAO",
            "NM_MEDICO_REQUISITANTE",
            "NM_PF_REALIZOU",
            "DS_CLASSIF_COR_TRANS",
            "DS_IE_CONTA_GERADA",
            "IE_POSSUI_AMOSTRA",
            "DS_SETOR_UNIDADE",
            "DS_FENOTIPO",
            "DS_FENOTIPO_PADRAO",
            "IE_PEND_PACIENTE",
            "IE_TRANSF_INICIADA",
            "IE_PRESCR_SUSP",
            "DT_INF_INICIADA",
            "DS_COR",
            "IE_HOUVE_REACAO",
            "CHK_DT_DISPENSACAO",
            "IE_POSSUI_PROD_UTIL"
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

def cabecalho_transfusao(codigo):
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return []

    cursor = connection.cursor()
    try:
        sql = """
            SELECT
                SUBSTR(TASY.obter_nome_pf(CD_PESSOA_FISICA), 1, 50) nome,
                TASY.obter_nome_pai_mae(cd_pessoa_fisica, 'M') as nome_mae,
                SUBSTR(TASY.obter_descricao_padrao('PESSOA_FISICA', 'IE_TIPO_SANGUE', CD_PESSOA_FISICA), 1, 2) ||
                        SUBSTR(TASY.obter_dados_pf(cd_pessoa_fisica, 'DSRH'), 1, 10) tipo_sangue,
                TASY.obter_data_nascto_pf(cd_pessoa_fisica) dt_nascimento,
                SUBSTR(TASY.OBTER_NOME_CONVENIO(TASY.obter_convenio_atendimento(nr_atendimento)), 1, 25) DS_CONVENIO
            FROM TASY.san_transfusao
            WHERE
                cd_pessoa_fisica = :codigo
        """

        # Executar consulta com o código como parâmetro
        params = {'codigo': codigo}
        cursor.execute(sql, params)

        keys = [
            "nome",
            "nome_mae",
            "tipo_sangue",
            "dt_nascimento",
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

def lista_captaçao():
    connection = obter_conexao()
    if connection is None:
        print("Connection is None.")
        return []

    cursor = connection.cursor()
    try:
        sql = """
            SELECT
                SUBSTR(TASY.obter_nome_pf(a.CD_PESSOA_FISICA), 1, 50) nome,
                SUBSTR(TASY.obter_descricao_padrao('PESSOA_FISICA', 'IE_TIPO_SANGUE', a.CD_PESSOA_FISICA), 1, 2) ||
                        SUBSTR(TASY.obter_dados_pf(a.cd_pessoa_fisica, 'DSRH'), 1, 10) tipo_sangue,
                TASY.obter_desc_tipo_doacao(a.nr_seq_tipo) as tipo_doacao,
                a.dt_doacao as dt_doacao,
                a.dt_retorno as dt_retorno,
                '+'||TASY.obter_dados_pf(a.cd_pessoa_fisica, 'TCD') as telefone,
                b.ie_sexo as sexo
            FROM TASY.san_doacao a
            JOIN TASY.pessoa_fisica b ON b.cd_pessoa_fisica = a.cd_pessoa_fisica
            WHERE
                a.ie_avaliacao_final = 'A'
            AND
                TRUNC(a.dt_doacao) >= TO_DATE(:data_inicial, 'DD-MM-YYYY')
            AND 
                TRUNC(a.dt_doacao) <= TO_DATE(:data_final, 'DD-MM-YYYY')
            ORDER BY 4 ASC
        """

        params = {
            'data_inicial': (datetime.now() - timedelta(days=90)).strftime('%d-%m-%Y'),
            'data_final': (datetime.now() - timedelta(days=60)).strftime('%d-%m-%Y')
        }
        cursor.execute(sql, params)

        keys = [
            "nome",
            "tipo_sangue",
            "tipo_doacao",
            "dt_doacao",
            "dt_retorno",
            "telefone",
            "sexo",
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
