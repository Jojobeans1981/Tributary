import Link from "next/link";

export default function NotFound() {
  return (
    <div className="bg-mist min-h-screen flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 rounded-full bg-foam text-current font-display font-bold text-2xl flex items-center justify-center mx-auto mb-6">
          ?
        </div>
        <h1 className="font-display text-abyss text-3xl font-bold mb-2">
          Page not found
        </h1>
        <p className="text-stone mb-6">
          The page you&rsquo;re looking for doesn&rsquo;t exist or has been moved.
        </p>
        <Link
          href="/dashboard"
          className="inline-block bg-current text-white font-bold px-6 py-3 rounded-input hover:bg-deep transition-colors"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
