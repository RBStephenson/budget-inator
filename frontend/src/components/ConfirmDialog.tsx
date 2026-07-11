import { useState, type ReactNode } from "react";

interface Props {
  title?: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  /** Red top-border accent, ⚠ icon, and a type-DELETE-to-confirm gate. */
  destructive?: boolean;
  /** Extra content rendered between the message and the action buttons — used
   *  for multi-item confirms (e.g. a rebalance move list). */
  children?: ReactNode;
  confirmDisabled?: boolean;
}

const DELETE_CONFIRM_WORD = "DELETE";

export function ConfirmDialog({
  title,
  message,
  confirmLabel = "Confirm",
  onConfirm,
  onCancel,
  destructive = false,
  children,
  confirmDisabled: confirmDisabledProp = false,
}: Props) {
  const [typedConfirm, setTypedConfirm] = useState("");
  const confirmDisabled =
    confirmDisabledProp || (destructive && typedConfirm !== DELETE_CONFIRM_WORD);

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div
        className={
          destructive
            ? "modal modal--sm confirm-dialog confirm-dialog--destructive"
            : "modal modal--sm confirm-dialog"
        }
      >
        <div className="confirm-dialog__icon" aria-hidden="true">
          {destructive ? "⚠" : "❓"}
        </div>
        {title && <h3 className="confirm-dialog__title">{title}</h3>}
        <p className="confirm-dialog__message">{message}</p>

        {children}

        {destructive && (
          <div className="form-field confirm-dialog__delete-gate">
            <label htmlFor="confirm-delete-input">
              Type {DELETE_CONFIRM_WORD} to confirm
            </label>
            <input
              id="confirm-delete-input"
              type="text"
              autoComplete="off"
              value={typedConfirm}
              onChange={(e) => setTypedConfirm(e.target.value)}
            />
          </div>
        )}

        <div className="confirm-dialog__actions">
          <button className="btn btn--ghost" onClick={onCancel}>
            Cancel
          </button>
          <button
            className={destructive ? "btn btn--danger" : "btn btn--primary"}
            onClick={onConfirm}
            disabled={confirmDisabled}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
