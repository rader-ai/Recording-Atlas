# Recovering the value in a recording archive

## The opportunity

Chris saw that his church had years of recorded sermons, but much of the value remained difficult to discover or reuse. Recording a sermon preserved it, yet a listener still needed to know which recording contained an answer and where to look within it.

## The original response

He created a content pipeline that transcribed audio, cleaned transcripts, divided content into passages, embedded those passages, and supported semantic search, a text archive, and questions and answers. The original implementation included choices around local versus cloud transcription, source timestamps, incremental processing, and checks intended to keep generated material faithful to the source.

Code reviewed for this reconstruction explains two specific needs: older audio had little searchable text, and transcribed answers needed concise written entry points. Those comments explain implementation intent; they do not independently establish adoption or outcome metrics.

## Making it reusable

The public reconstruction adds an onboarding experience so someone else can configure the needed services and process a first recording. Setup explains requirements and data movement. Discovery identifies recordings before paid processing. Saved jobs allow recovery. Archive views preserve source context, and draft answers quote source passages for review.

The local example path offers a way to inspect the product without credentials. The real content path uses provider adapters and requires the user's own API access. The reconstruction is smaller than the original and does not imply the same deployment scale or feature completeness.

## Product decisions on display

Discovery comes before acquisition and paid work. A video reference is distinct from permission and technical access to its captions or media. One recording is the first success milestone. Raw transcripts remain separate from readable versions. Repeated indexing reuses unchanged content. Generated content remains a draft. Setup asks only for accounts needed by selected features.

## Evidence boundaries

The local example flow and automated tests were executed. Paid transcription, live provider generation, and authenticated YouTube discovery were not run during preparation. No quantitative user outcome or semantic accuracy claim is made for this reconstruction. The supplied query evaluation is a synthetic development set.
