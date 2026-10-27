"""Build a MySQL URL without asking users to percent-encode their passwords."""
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


def build_database_url(environment):
    fields = {}
    for key, value in environment.items():
        if value or key.upper() not in fields:
            fields[key.upper()] = value
    username = fields.get('DB_USERNAME') or fields.get('DB_USER')
    database = fields.get('DB_NAME')
    # Once credentials/name are provided, separate fields take precedence over
    # an older DATABASE_URL. Accept DB_username/db_pass as well as uppercase keys.
    if username or database:
        if not username or not database:
            raise ValueError('Fill both DB_USERNAME and DB_NAME in the private .env.')
        try:
            port = int(fields.get('DB_PORT') or '3306')
            if not 1 <= port <= 65535: raise ValueError()
        except (ValueError, TypeError):
            raise ValueError('DB_PORT must be a number between 1 and 65535.') from None
        return URL.create('mysql+pymysql', username=username,
                          password=fields.get('DB_PASSWORD') or fields.get('DB_PASS') or '',
                          host=fields.get('DB_HOST') or '127.0.0.1', port=port,
                          database=database, query={'charset': 'utf8mb4'})
    try:
        url = make_url(fields.get('DATABASE_URL') or 'mysql+pymysql://localhost/ilma?charset=utf8mb4')
    except (ArgumentError, ValueError):
        raise ValueError('Fill DB_HOST, DB_PORT, DB_NAME, DB_USERNAME and DB_PASSWORD in the private .env.') from None
    if url.get_backend_name() != 'mysql':
        raise ValueError('Runtime database must use MySQL. SQLite is only for isolated tests.')
    if url.drivername == 'mysql': url = url.set(drivername='mysql+pymysql')
    return url.update_query_dict({'charset': 'utf8mb4'})
