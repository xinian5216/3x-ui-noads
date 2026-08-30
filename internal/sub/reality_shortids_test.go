package sub

import (
	"net/url"
	"reflect"
	"testing"
)

const rotatingRealityStream = `{
	"network":"tcp",
	"security":"reality",
	"tcpSettings":{"header":{"type":"none"}},
	"realitySettings":{
		"serverNames":["reality.example.com"],
		"shortIds":["aa11","bb22"],
		"settings":{"publicKey":"PBKvalue","fingerprint":"chrome","spiderX":"/"}
	}
}`

func TestActiveRealityShortIDs(t *testing.T) {
	tests := []struct {
		name        string
		value       any
		activeCount int
		want        []string
	}{
		{
			name:        "rotation exposes active prefix only",
			value:       []any{"new-a", "new-b", "retiring-a", "retiring-b"},
			activeCount: 2,
			want:        []string{"new-a", "new-b"},
		},
		{
			name:        "zero preserves legacy behavior",
			value:       []any{"one", "two"},
			activeCount: 0,
			want:        []string{"one", "two"},
		},
		{
			name:        "string slice is accepted",
			value:       []string{"one", "two"},
			activeCount: 1,
			want:        []string{"one"},
		},
		{
			name:        "invalid active value does not expose retiring suffix",
			value:       []any{42, "retiring"},
			activeCount: 1,
			want:        []string{},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := activeRealityShortIDs(tt.value, tt.activeCount)
			if !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("activeRealityShortIDs() = %#v, want %#v", got, tt.want)
			}
		})
	}
}

func TestRotatingRealityShareLinkPublishesOnlyActiveShortID(t *testing.T) {
	inbound := shareLinkInbound(rotatingRealityStream)
	inbound.RealityShortIdsActiveCount = 1

	link := (&SubService{}).genVlessLink(inbound, "user")
	parsed, err := url.Parse(link)
	if err != nil {
		t.Fatalf("parse share link: %v", err)
	}
	if got := parsed.Query().Get("sid"); got != "aa11" {
		t.Fatalf("share link sid = %q, want active shortId %q", got, "aa11")
	}
}

func TestRotatingRealityJSONPublishesOnlyActiveShortID(t *testing.T) {
	stream := (&SubJsonService{}).streamDataWithActiveRealityIDs(rotatingRealityStream, "client", 1)
	reality, ok := stream["realitySettings"].(map[string]any)
	if !ok {
		t.Fatalf("realitySettings has type %T", stream["realitySettings"])
	}
	if got := reality["shortId"]; got != "aa11" {
		t.Fatalf("JSON shortId = %#v, want active shortId %q", got, "aa11")
	}
}

func TestRotatingRealityClashPublishesOnlyActiveShortID(t *testing.T) {
	stream := (&SubClashService{}).streamDataWithActiveRealityIDs(rotatingRealityStream, 1)
	reality, ok := stream["realitySettings"].(map[string]any)
	if !ok {
		t.Fatalf("realitySettings has type %T", stream["realitySettings"])
	}
	if got := reality["shortId"]; got != "aa11" {
		t.Fatalf("Clash shortId = %#v, want active shortId %q", got, "aa11")
	}
}
