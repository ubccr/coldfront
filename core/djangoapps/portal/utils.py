
def generate_publication_by_year_chart_data(publications_by_year):

    years, publications = zip(*publications_by_year)
    years = list(years)
    publications = list(publications)
    years.insert(0, "Year")
    publications.insert(0, "Publications")

    data = {
        "x": "Year",
        "columns": [
            years,
            publications
        ],
        "type": "bar",
        "colors": {
            "Publications": '#17a2b8'
        }
    }

    return data


def generate_total_grants_by_agency_chart_data(total_grants_by_agency):

    grants_agency_chart_data = {
        "columns": total_grants_by_agency,
        "type": 'donut'
    }


    print(grants_agency_chart_data)
    return grants_agency_chart_data
