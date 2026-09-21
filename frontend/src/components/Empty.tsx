import './Empty.css';

// A reusable honest empty state. Used everywhere a feature isn't finalised.
// Per the build rule: unfinalised things are genuinely empty, and say why.
export default function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty">
      <div className="empty-mark" aria-hidden>—</div>
      <div className="empty-title">{title}</div>
      <div className="empty-body">{body}</div>
    </div>
  );
}
