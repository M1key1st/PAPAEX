from dataclasses import dataclass
from math import ceil


@dataclass
class Page:
    items: list
    page: int
    per_page: int
    total: int

    @property
    def pages(self):
        return max(1, ceil(self.total / self.per_page))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def next_num(self):
        return self.page + 1

    def iter_pages(self, window=2):
        """Sahifalash tugmalari uchun: 1 ... p-2 p-1 p p+1 p+2 ... N ko'rinishida raqamlar beradi."""
        pages = self.pages
        result = []
        for p in range(1, pages + 1):
            if p == 1 or p == pages or (self.page - window <= p <= self.page + window):
                result.append(p)
            elif result and result[-1] is not None:
                result.append(None)
        # None qatorlarini bittaga siqish
        cleaned = []
        for p in result:
            if p is None and cleaned and cleaned[-1] is None:
                continue
            cleaned.append(p)
        return cleaned


def paginate(db, base_query, count_query, params, page, per_page):
    page = max(1, page)
    total = db.execute(count_query, params).fetchone()[0]
    offset = (page - 1) * per_page
    rows = db.execute(
        f"{base_query} LIMIT ? OFFSET ?", list(params) + [per_page, offset]
    ).fetchall()
    return Page(items=rows, page=page, per_page=per_page, total=total)
