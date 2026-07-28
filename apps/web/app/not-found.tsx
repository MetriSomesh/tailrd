import { ButtonLink } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main
      id="main"
      className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-6 text-center"
    >
      <p className="font-mono text-2xs uppercase tracking-widest text-fg-quaternary">
        Error 404
      </p>
      <h1 className="type-display mt-4 text-4xl text-fg">Page not found</h1>
      <p className="mt-3 text-pretty text-sm leading-relaxed text-fg-tertiary">
        The page you&apos;re looking for doesn&apos;t exist or may have moved.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <ButtonLink href="/">Go home</ButtonLink>
        <ButtonLink href="/dashboard" variant="secondary">
          Dashboard
        </ButtonLink>
      </div>
    </main>
  );
}
