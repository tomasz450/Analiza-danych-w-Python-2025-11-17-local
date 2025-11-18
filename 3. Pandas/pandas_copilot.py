"""Simple helper for loading the `movies` CSV and computing top films by genre.

This simplified version uses only pandas: `pd.read_csv(url)` to load remote
CSV files directly. It keeps the same analysis function but removes the
requests/certifi wrapper.
"""
from __future__ import annotations

import sys
from typing import Optional

import pandas as pd


def read_csv_simple(url: str, **kwargs) -> pd.DataFrame:
    """Load a CSV directly with pandas from a URL.

    Parameters
    - url: CSV URL
    - kwargs: forwarded to `pd.read_csv`
    """
    return pd.read_csv(url, **kwargs)


def top_genres_top_movies(
    movies: pd.DataFrame, top_n_genres: int = 5, top_n_movies: int = 5
) -> pd.DataFrame:
    """Return top films for the top N genres using only pandas.

    Genres are ranked by title count. For each top genre we select up to
    `top_n_movies` ordered by `star_rating` (missing ratings treated as -1).
    """
    if 'genre' not in movies.columns:
        raise ValueError("Input DataFrame must contain a 'genre' column")

    top_genres = movies['genre'].value_counts().nlargest(top_n_genres).index.tolist()

    frames = []
    for g in top_genres:
        dfg = movies[movies['genre'] == g].copy()
        if 'star_rating' in dfg.columns:
            dfg = dfg.assign(_sr=dfg['star_rating'].fillna(-1))
            dfg = dfg.sort_values('_sr', ascending=False)
        cols = [c for c in ('title', 'star_rating', 'duration', 'genre') if c in dfg.columns]
        sel = dfg.loc[:, cols].head(top_n_movies).copy()
        sel.insert(0, 'genre_group', g)
        frames.append(sel)

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    return result


def main(argv: Optional[list[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    movies_url = 'https://bit.ly/imdbratings'
    print('Downloading movies dataset with pandas...')
    try:
        movies = read_csv_simple(movies_url)
    except Exception as e:
        print('Failed to download or parse movies CSV:', e)
        return 1

    print(f'movies: {len(movies):,} rows, columns: {list(movies.columns)}')

    print('Computing top genres and top films...')
    result = top_genres_top_movies(movies, top_n_genres=5, top_n_movies=5)

    if result.empty:
        print('No result produced (check that movies contains expected columns).')
        return 1

    print('\nTop films for top 5 genres:')
    print(result.to_string(index=False))

    out = 'top5_genres_top_movies.csv'
    result.to_csv(out, index=False)
    print(f'Wrote result to {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
