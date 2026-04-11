import type { ReactElement } from "react";

interface FigureGalleryProps {
  figures: Array<{
    src: string;
    alt: string;
    caption: string;
  }>;
}

export function FigureGallery({ figures }: FigureGalleryProps): ReactElement {
  return (
    <section className="figure-gallery" aria-label="Generated benchmark figures">
      {figures.map((figure) => (
        <figure className="figure-panel" key={figure.src}>
          <img src={figure.src} alt={figure.alt} loading="lazy" />
          <figcaption>{figure.caption}</figcaption>
        </figure>
      ))}
    </section>
  );
}
