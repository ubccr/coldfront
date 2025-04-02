function Table({ rows, headers, className = "" }) {
  return (
    <table className={`${className} table table-sm`}>
      <thead>
        <tr>{headers}</tr>
      </thead>
      <tbody className="table-tbody">{rows}</tbody>
    </table>
  );
}

export default Table;
