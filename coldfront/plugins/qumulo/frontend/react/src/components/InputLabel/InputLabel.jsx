import { useState } from "react";

import "./InputLabel.css";

function InputLabel({ label, value = "", onChange }) {
  const [isActive, setIsActive] = useState(false);
  const [internalValue, setInternalValue] = useState(value);

  const onKeyDown = (event) => {
    if (event.key === "Enter") {
      onChange(internalValue);
      setIsActive(false);
    }
  };

  return (
    <>
      {!isActive && !value ? (
        <span className="pointer" onClick={() => setIsActive(true)}>
          {label}
          <sup>
            <i className="fas fa-search" style={{ color: "blue" }}></i>
          </sup>
        </span>
      ) : (
        <input
          type="text"
          value={internalValue}
          onChange={(e) => setInternalValue(e.target.value)}
          onKeyDown={onKeyDown}
          autoFocus
        />
      )}
    </>
  );
}

export default InputLabel;
