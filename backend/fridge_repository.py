def _public_ingredient(row):
    return {
        "id": row[0],
        "name": row[1],
        "category": row[2],
        "image": row[3],
        "selected": True,
    }


def list_user_ingredients(conn):
    rows = conn.execute(
        "SELECT id, name, category, image FROM user_ingredients"
    ).fetchall()
    return [_public_ingredient(row) for row in rows]


def insert_user_ingredient(conn, *, name, category, image):
    cursor = conn.execute(
        """
        INSERT INTO user_ingredients (name, category, quantity, image)
        VALUES (?, ?, NULL, ?)
        """,
        (name, category, image),
    )
    conn.commit()
    return {
        "id": cursor.lastrowid,
        "name": name,
        "category": category,
        "image": image,
        "selected": True,
    }
