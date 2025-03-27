import "./SortButtons.css";

const SortButtons = ({ onClick, label, name }) => {
  return (
    <>
      <a className="sort-asc" onClick={() => onClick(name)}>
        <i className="fas fa-sort-up" aria-hidden="true"></i>
        <span className="sr-only">Sort {label} asc</span>
      </a>
      <a className="sort-desc" onClick={() => onClick(`-${name}`)}>
        <i className="fas fa-sort-down" aria-hidden="true"></i>
        <span className="sr-only">Sort {label} desc</span>
      </a>
    </>
  );
};

export default SortButtons;
