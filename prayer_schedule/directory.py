"""Church directory data and CSV parsing.

The complete 161-family directory is embedded as a Python string constant so
the project remains a zero-dependency, single-repository deliverable.
``parse_directory`` converts the CSV into a sorted list of ``"Last, First"``
strings and performs defensive validation (missing columns, blank names,
duplicates).
"""

from __future__ import annotations

import csv
from io import StringIO


# Church Directory CSV - All 161 families
DIRECTORY_CSV: str = """Last Name,First Names
Allred,"Patric & Courtney; Brady Hoyt, Allie Grace"
Austin,Shawn
Badger,Marvin & Kathy
Baisley,Teresa
Barnwell,"Michele; Taylor"
Beach,Bruce
Beaty,Ethel
Beaty,Gene & Norma
Bell,Jim & Beth
Benedict,Larry & Peggy
Blyly,"Garrett & Taylor; Ellison, Bellamy"
Bohannon,Frank & Paula
Bow,Katherine
Brady,Donald & Donna
Brewer,Sandra
Brock,Lilly
Brock,"Philip & Brooke; Olliver (Ollie), Thea"
Brown,Connie
Brown,Earl
Brown,Eddie
Brown,"Harold & Arlene"
Brown,Kim
Brown,Wilma
Burchenal,Robert
Burnette,Howard & Kathy
Bush,"John & Sunshine; Serena, Sydney"
Cairns,Rod & Starla
Clark,"Sandra; Silas, Sydney"
Cole,Aprel
Comer,Gail
Cosentini,"Victor & Paige; Cooper"
Crabtree,Tommy & Cathy
Davis,Gail
Davis,J.C. & Lana
Delmonte,Steve & Jenny
Dodson,Bendell
Edwards,Emily
Evans,Janie
Fairman,"Kyle & Leigh Ann; Wyatt, Audrey"
Fawehinmi,Ethan
Folk,Roberta
Fowler,Rick & Sue
Fox,Jean
Fox,L.A. & Cindy
Fox,Richard
Fulford,Sharon
Graham,Pat
Griffies,David & Mary
Griffin,Donna & Wendell
Griffin,"Dylan & Julia; Eli, Noah, Isaiah"
Haga,David & Patty
Hall,Robin
Harris,Jimmy & Donna
Hassler,Rebecca
Hassler,Steve & Barbara
Hawn,Daniel
Haymon,Vernon
Haynes,Cameron & Evette
Hedgecoth,Myra
Hennessee,"Dale & Charlotte; Kadrienne, Kambry"
Hollars,Kathy
Hoover,Buddy & Jane
Houston,"Jeanene & Steve; Stevie"
Houston,Ruby
Hudson,Brett
Hughes,Dona
Hunt,Jeff & Sonia
Hunt,Wendell & Betty
Isaacson,Michael & Terry
Iverson,Don & Cathy
Jackson,Gene & Thelda
Jackson,Robert & Tracy
Jenkins,Miriam
Judd,"Alan & Amy; Anderson, Adrian, Adam"
Keck,"Jim & Andrea; Conner, Emily"
Kerley,Marvin & Rachel
Kimbro,Sue
Lane,Patsy
Lau,"Gary & Hannah; David, Maren, Major"
Law,Stephen Charles
Lipe,David & Linda
Loveday,Coye
Loveday,"Doug & Wendy; Amy"
Loveday,"Jonathan & Sylvia; Jabin"
Madden,Cassey
Marshall,Brenda
Martin,"David & Elissa; Reid, Landyn, Avery"
Martin,Jaton
Maxwell,Sue
Maynard,Betty
McCormick,Michael & Ginger
McDuffee,Larry & Linda
McGhee,Jason & Sara
McLaughlin,Brian & Heather
Meadows,Ted & Elaine
Mitchell,Jeanette
Mize,Aileen
Mize,Al & Elaine
Napier,Natalie
O'Dell,Betty & Bill
O'Guin,Linda
Parham,"Johnny & Charity; Eli"
Parham,Jordan
Parham,"Tom & Jill; Brantley"
Parsons,Charles
Pernell,Jerry & Tammi
Pierce,Chris & Alex
Potter,Rhonda & David
Pritt,Judy
Pritt,"Scott & Kellee"
Randolph,Clyde & Betty
Rector,Mary
Rector,"Troy; Kadence"
Redwine,Chris & Dana
Reed,Ima Jeanne
Reed,"Nathan & Sara; Ridley, Beau, Tate"
Rives,Marla
Roberts,"Jackson & Kayla; Jensen"
Roberts,"Jared & Shavonna; Dylan, Lola, Evan"
Roberts,Mark & Lynn
Roberts,"Matt & Jody; Tony, Ethan, Sheridan"
Rose,Lisa
Rothery,Ginny
Savage,"Brandon & Jenny; Clara, Charlotte"
Saylors,John & Linda
Sears,"Jake & Baylee; Summit, Jett"
Seiber,"Seth & Madison; Kayson, Kendall"
Selby,"Brian; Gavin"
Simmons,Bruce & Louise
Slate,Ray & Martha
Smith,Joe Lee
Smith,Roger & Dianna
Smith,Scott & Juanita
Sparks,Carol
Sparks,Jerry & Judy
Stevens,Kyle & Laura Li
Stover,Lewis & Judy
Swafford,"Russell & Christiana; Jeremiah, Lilly, Tempest"
Thomas,Elon & Betty
Thompson,"Christopher & Brittany; Nautica"
Trotter,Linda
Vaden,David & Sheila
Vaughn,Dennis & Diane
Walker,Barbara
Warner,Jean
Weathers,"Barry & Nancy"
Webb,Richard & Sylvia
Wells,Martha
White,Doris
Whittenburg,Dan & Johnnie
Wiese,Allena (A- lynn-a)
Wilson,Ray
Wood,"Chase & Abby; Lakelyn, Landry"
Wood,Jerry & Rebecca
Wootton,Rebecca
Wyatt,"Jason & Rachel; Mason"
Wyatt,"Stephanie; Sue Ann"
Wyatt,Sarah
Young,Donna & David
Young,Mickey & Pat
Young,Scott"""


def parse_directory(csv_content: str | None = None) -> list[str]:
    """Parse a directory CSV into a sorted list of ``"Last, First"`` strings.

    ``csv_content`` defaults to the embedded :data:`DIRECTORY_CSV`. Accepting
    an override keeps the function pure and easy to unit-test with synthetic
    inputs.

    Validation performed (raises :class:`ValueError` with row/family context):

    * empty rows are skipped silently
    * missing required columns raises with the row number
    * empty ``Last Name`` or ``First Names`` raises with the row number
    * duplicate family strings raise with the full list of duplicates
    """
    if csv_content is None:
        csv_content = DIRECTORY_CSV
    all_families: list[str] = []
    csv_reader = csv.DictReader(StringIO(csv_content))

    required_columns = {"Last Name", "First Names"}
    # DictReader sets fieldnames after the first read; calling .fieldnames
    # triggers the header parse if it hasn't happened yet.
    fieldnames = csv_reader.fieldnames or []
    missing_cols = required_columns - set(fieldnames)
    if missing_cols:
        raise ValueError(
            f"DIRECTORY_CSV is missing required columns: {sorted(missing_cols)}"
        )

    # ``row_number`` counts data rows starting at 2 (row 1 is the header).
    for row_number, row in enumerate(csv_reader, start=2):
        # Skip completely empty rows (all values None or "").
        if not row or all(not (v or "").strip() for v in row.values()):
            continue

        try:
            last_name = row["Last Name"]
            first_names = row["First Names"]
        except KeyError as exc:
            raise ValueError(
                f"DIRECTORY_CSV row {row_number}: missing column {exc!s}"
            ) from exc

        if last_name is None or not str(last_name).strip():
            raise ValueError(
                f"DIRECTORY_CSV row {row_number}: empty 'Last Name' field"
            )
        if first_names is None or not str(first_names).strip():
            raise ValueError(
                f"DIRECTORY_CSV row {row_number}: empty 'First Names' field"
            )

        family_name = f"{last_name}, {first_names}"
        all_families.append(family_name)

    # Detect duplicates (same family string appearing more than once).
    seen: set[str] = set()
    duplicates: list[str] = []
    for fam in all_families:
        if fam in seen:
            duplicates.append(fam)
        else:
            seen.add(fam)
    if duplicates:
        # Preserve encounter order but deduplicate the duplicates list itself.
        unique_duplicates = list(dict.fromkeys(duplicates))
        raise ValueError(
            f"DIRECTORY_CSV contains duplicate families: {unique_duplicates}"
        )

    return sorted(all_families)
