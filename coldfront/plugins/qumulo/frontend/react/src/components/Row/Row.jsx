function Row({ allocation, isChecked, onAllocationCheck, columns }) {
  return (
    <tr
      key={allocation.id}
      className={`text-nowrap ${isChecked ? "checked" : ""}`}
    >
      <td key="checkbox">
        <input
          type="checkbox"
          id={`allocation-${allocation.id}`}
          value={allocation.id}
          checked={isChecked}
          onChange={onAllocationCheck}
        />
      </td>
      {columns.map(({ key, label }) => (
        <td key={key} className="text-nowrap">
          {allocation[key]}
        </td>
      ))}
    </tr>
  );
}

export default Row;
