import { Link } from "./Link";

export function NotFound() {
  return (
    <div className="not-found">
      <h2 className="not-found__title">Page not found</h2>
      <p className="not-found__body">
        The page you&apos;re looking for doesn&apos;t exist.
      </p>
      <Link href="/" className="btn btn--primary">
        ← Go to dashboard
      </Link>
    </div>
  );
}
