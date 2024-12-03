import logging
from ldap3 import Server, Connection, ALL
import cx_Oracle, base64

logger = logging.getLogger(__name__)


def exists_ad(username, password):
    ldap_server = 'ldap://10.0.1.253'  # Substitua pelo endereço do servidor LDAP
    ldap_port = 389  # Porta LDAP padrão
    # Substitua pelo seu nome de usuário LDAP
    ldap_user = f'{username}@honcord.local'
    ldap_password = password

    server = Server(ldap_server, port=ldap_port, get_info=ALL)

    try:
        conn = Connection(server, user=ldap_user,
                          password=ldap_password, auto_bind=True)

        if conn.bind():
            logger.info(
                f"Usuário {username} autenticado com sucesso via LDAP.")
            return {'username': username}
        else:
            logger.error(
                f"Autenticação LDAP falhou para usuário {username}: {conn.result}")
            return None

    except Exception as e:
        logger.error(f"LDAP authentication failed for user {username}: {e}")
        return None


def tasy_user_data(username):
    # Configurar a conexão manual ao banco Oracle
    # Verifique a porta e service_name
    dsn_tns = cx_Oracle.makedsn('10.0.1.12', '1521', service_name='dbprod')
    connection = cx_Oracle.connect(
        user='AUGUSTO', password='Mudar@123', dsn=dsn_tns)
    cursor = connection.cursor()

    query = """
        SELECT cd_pessoa_fisica as IDtasy, TASY.OBTER_NOME_PF(cd_pessoa_fisica) as name, im_pessoa_fisica as foto
        FROM TASY.PESSOA_FISICA_FOTO
        WHERE nm_usuario = :username
    """

    cursor.execute(query, username=username)
    result = cursor.fetchone()
    cursor.close()
    connection.close()

    if result:
        idtasy, name, foto = result
        # Se houver uma foto, converte para base64
        foto_base64 = base64.b64encode(foto).decode('utf-8') if foto else None
        return {'IDtasy': idtasy, 'name': name, 'foto': foto_base64}
    return None
