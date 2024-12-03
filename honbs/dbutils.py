# db_utils.py
import cx_Oracle
from django.conf import settings


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