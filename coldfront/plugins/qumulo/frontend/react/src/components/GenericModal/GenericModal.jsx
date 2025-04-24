import { useEffect } from "react";

function GenericModal({ title, text, onAction, actionTest, onClose }) {
  return (
    <div className="modal" style={{ display: "block" }} role="dialog">
      <div className="modal-dialog" role="document">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">{title}</h5>
            <button
              type="button"
              className="close"
              data-dismiss="modal"
              aria-label="Close"
              onClick={onClose}
            >
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
          <div className="modal-body">
            <p>{text}</p>
          </div>
          <div className="modal-footer">
            {onAction && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={onAction}
              >
                {actionTest || "Save changes"}
              </button>
            )}
            <button
              type="button"
              className="btn btn-secondary"
              data-dismiss="modal"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default GenericModal;
