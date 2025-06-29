from youtube_transcript_api import YouTubeTranscriptApi
import re
from urllib.parse import urlparse, parse_qs

def extract_video_id_urllib(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com', 'youtu.be']:
        if parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:]  # / 제거
        else:
            query_params = parse_qs(parsed_url.query)
            return query_params.get('v', [None])[0]
    return None

def main():
    ytt_api = YouTubeTranscriptApi()
    
    video_link = "https://www.youtube.com/watch?v=BIvuigQkelk"
    video_id = extract_video_id_urllib(video_link)

    transcript = ytt_api.fetch(video_id, languages=['ko'])

    # 텍스트를 파일로 저장
    output_filename = f"transcript_{video_id}.txt"
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        for snippet in transcript:
            f.write(snippet.text + '\n')
    
    print(f"자막이 {output_filename} 파일로 저장되었습니다.")
    print(f"총 {len(transcript)}개의 자막 조각이 저장되었습니다.")


if __name__ == "__main__":
    main()

