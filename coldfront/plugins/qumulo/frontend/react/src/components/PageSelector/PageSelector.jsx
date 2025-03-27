import { useState } from "react";

import "./PageSelector.css";

function PageSelector({
  currentPage,
  setCurrentPage,
  totalPages,
  maxContinous = 5,
}) {
  const renderContinousPages = () => {
    return Array.from(Array(totalPages)).map((_, index) => (
      <li
        className={`page-item ${index + 1 === currentPage && "active"}`}
        key={index}
      >
        <button className="page-link" onClick={() => onChangePage(index + 1)}>
          {index + 1}
        </button>
      </li>
    ));
  };

  const renderNonContinousPages = () => {
    const [thisPage, setThisPage] = useState(currentPage);

    return (
      <li className="page-item">
        <input
          type="number"
          className="page-link"
          value={thisPage}
          onChange={(event) => setThisPage(Number(event.target.value))}
          onKeyDown={(event) =>
            event.key === "Enter" && onChangePage(event.target.value)
          }
          min="1"
          max={totalPages}
        />
      </li>
    );
  };

  const onChangePage = (rawValue) => {
    let value = Number(rawValue);
    if (value < 1) {
      value = 1;
    }
    if (value > totalPages) {
      value = totalPages;
    }

    setCurrentPage(value);
  };

  return (
    totalPages > 1 && (
      <ul className="pagination">
        <li className="page-item">
          <button
            className="page-link"
            aria-label="Previous"
            onClick={() => onChangePage(currentPage - 1)}
          >
            <span aria-hidden="true">&laquo;</span>
            <span className="sr-only">Previous</span>
          </button>
        </li>
        {totalPages <= maxContinous && renderContinousPages()}
        {totalPages > maxContinous && renderNonContinousPages()}
        <li className="page-item">
          <button
            className="page-link"
            aria-label="Next"
            onClick={() => onChangePage(currentPage + 1)}
          >
            <span aria-hidden="true">&raquo;</span>
            <span className="sr-only">Next</span>
          </button>
        </li>
      </ul>
    )
  );
}

export default PageSelector;
