/**
 * TypeScript types for the boomoorlog Supabase schema.
 *
 * Hand-written (NOT auto-generated). The Supabase CLI's `gen types` requires
 * Docker/Podman locally; for a 2-table schema it's faster to maintain by hand.
 * Keep in sync with db/001_schema.sql.
 *
 * Shape matches @supabase/postgrest-js's `GenericSchema`:
 *   { Tables, Views, Functions } where each Table has
 *   { Row, Insert, Update, Relationships }. Without the trailing fields,
 *   `.from()` falls back to `never` row types.
 *
 * If the schema changes, edit this file in the same PR as the migration.
 */

export type Database = {
  public: {
    Tables: {
      genera: {
        Row: {
          slug: string;
          latin_name: string;
          dutch_name: string | null;
          display_name: string | null;
          attack: number | null;
          range: number | null;
          health: number | null;
          attack_speed: number | null;
          move_speed: number | null;
          world_rarity_multiplier: number;
          avg_height_m: number | null;
          avg_diameter_cm: number | null;
          personality: string | null;
          tree_count: number;
          sprite_path: string | null;
          lore: string | null;
          created_at: string;
        };
        Insert: {
          slug: string;
          latin_name: string;
          dutch_name?: string | null;
          display_name?: string | null;
          attack?: number | null;
          range?: number | null;
          health?: number | null;
          attack_speed?: number | null;
          move_speed?: number | null;
          world_rarity_multiplier?: number;
          avg_height_m?: number | null;
          avg_diameter_cm?: number | null;
          personality?: string | null;
          tree_count?: number;
          sprite_path?: string | null;
          lore?: string | null;
          created_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["genera"]["Insert"]>;
        Relationships: [];
      };
      trees: {
        Row: {
          id: number;
          genus_slug: string | null;
          species_full: string | null;
          species_top: string | null;
          postcode6: string | null;
          postcode4: string | null;
          buurt_id: string | null;
          longitude: number | null;
          latitude: number | null;
          rd_x: number | null;
          rd_y: number | null;
          geometrie_raw: string | null;
          height_class: string | null;
          diameter_class: string | null;
          height_m: number | null;
          diameter_cm: number | null;
          planting_year: number | null;
          owner: string | null;
          manager: string | null;
          location: string | null;
          location_detail: string | null;
          object_type: string | null;
          species_type: string | null;
          growing_location_id: string | null;
          protection_status: string | null;
          protection_status_detail: string | null;
          valid_from: string | null;
          mutated_at: string | null;
        };
        Insert: Database["public"]["Tables"]["trees"]["Row"];
        Update: Partial<Database["public"]["Tables"]["trees"]["Insert"]>;
        Relationships: [
          {
            foreignKeyName: "trees_genus_slug_fkey";
            columns: ["genus_slug"];
            isOneToOne: false;
            referencedRelation: "genera";
            referencedColumns: ["slug"];
          },
        ];
      };
      observations: {
        Row: {
          source: "inat" | "waarneming";
          source_obs_id: number;
          observed_on: string;
          // `point` is PostGIS geography — supabase-js returns hex EWKB. We
          // never select it from the client; lat/lng below are the consumable
          // copy. Typed as unknown so accidental use surfaces a TS error.
          point: unknown;
          lat: number | null;
          lng: number | null;
          accuracy_m: number | null;
          scientific_name: string;
          common_name: string | null;
          taxon_group: string | null;
          quality: string | null;
          photo_url: string | null;
          photo_license: string | null;
          permalink: string | null;
          creature_slug: string | null;
          fetched_at: string;
        };
        Insert: Database["public"]["Tables"]["observations"]["Row"];
        Update: Partial<Database["public"]["Tables"]["observations"]["Insert"]>;
        Relationships: [
          {
            foreignKeyName: "observations_creature_slug_fkey";
            columns: ["creature_slug"];
            isOneToOne: false;
            referencedRelation: "creatures";
            referencedColumns: ["slug"];
          },
        ];
      };
      creatures: {
        Row: {
          slug: string;
          common_name: string;
          latin_name: string | null;
          pic_file: string | null;
          tree_count: number;
          tree_genera: string[];
          form: string | null;
          // future-proof game stats — all nullable until populated.
          attack: number | null;
          range: number | null;
          health: number | null;
          attack_speed: number | null;
          move_speed: number | null;
          created_at: string;
          // Added in migration 012 — auto-promoted creatures from iNat/waarneming.
          source: "curated" | "auto_observed";
          promoted_at: string | null;
          taxon_group: string | null;
          wikipedia_summary: string | null;
          observations_count: number;
          sprite_pending: boolean;
        };
        Insert: {
          slug: string;
          common_name: string;
          latin_name?: string | null;
          pic_file?: string | null;
          tree_count?: number;
          tree_genera?: string[];
          form?: string | null;
          attack?: number | null;
          range?: number | null;
          health?: number | null;
          attack_speed?: number | null;
          move_speed?: number | null;
          created_at?: string;
          source?: "curated" | "auto_observed";
          promoted_at?: string | null;
          taxon_group?: string | null;
          wikipedia_summary?: string | null;
          observations_count?: number;
          sprite_pending?: boolean;
        };
        Update: Partial<Database["public"]["Tables"]["creatures"]["Insert"]>;
        Relationships: [];
      };
    };
    Views: Record<string, never>;
    Functions: {
      trees_within_radius: {
        Args: {
          lat: number;
          lng: number;
          radius_m?: number;
        };
        Returns: Database["public"]["Tables"]["trees"]["Row"][];
      };
      trees_in_bbox: {
        Args: {
          lat_min: number;
          lng_min: number;
          lat_max: number;
          lng_max: number;
        };
        Returns: Database["public"]["Tables"]["trees"]["Row"][];
      };
      trees_for_view: {
        Args: {
          lat_min: number;
          lng_min: number;
          lat_max: number;
          lng_max: number;
          max_pins: number;
          cells_per_side: number;
        };
        Returns: Array<{
          mode: "individual" | "cluster";
          cell_key: string;
          id: number | null;
          lat: number;
          lng: number;
          slug: string | null;
          n: number;
          species: string | null;
          height_m: number | null;
          diameter_cm: number | null;
          planting_year: number | null;
          location: string | null;
          location_detail: string | null;
          protection_status: string | null;
        }>;
      };
      trees_top_genera_in_bbox: {
        Args: {
          lat_min: number;
          lng_min: number;
          lat_max: number;
          lng_max: number;
          limit_n: number;
        };
        Returns: Array<{
          slug: string;
          n: number;
          total: number;
        }>;
      };
    };
  };
};

export type Genus = Database["public"]["Tables"]["genera"]["Row"];
export type Tree = Database["public"]["Tables"]["trees"]["Row"];
export type Creature = Database["public"]["Tables"]["creatures"]["Row"];
export type Observation = Database["public"]["Tables"]["observations"]["Row"];
