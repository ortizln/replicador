from flask import request


def paginar_ordenar(query, model, default_sort="id", default_order="asc"):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    sort_by = request.args.get("sort_by", default_sort)
    sort_order = request.args.get("sort_order", default_order)

    col = getattr(model, sort_by, None)
    if col is None:
        col = getattr(model, default_sort)

    if sort_order == "desc":
        query = query.order_by(col.desc())
    else:
        query = query.order_by(col.asc())

    pag = query.paginate(page=page, per_page=per_page, error_out=False)
    return pag, page, per_page
