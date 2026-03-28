"use client";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="bg-mist min-h-screen flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 rounded-full bg-stop-light text-stop font-display font-bold text-2xl flex items-center justify-center mx-auto mb-6">
          !
        </div>
        <h1 className="font-display text-abyss text-3xl font-bold mb-2">
          Something went wrong
        </h1>
        <p className="text-stone mb-6">
          An unexpected error occurred. Please try again.
        </p>
        <button
          onClick={reset}
          className="inline-block bg-current text-white font-bold px-6 py-3 rounded-input hover:bg-deep transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
