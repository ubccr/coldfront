function Table({ rows, headers }) {
  return (
    <table className="table table-sm">
      <thead>
        <tr>{headers}</tr>
      </thead>
      <tbody className="table-values-tbody">{rows}</tbody>
    </table>
  );
}

export default Table;
